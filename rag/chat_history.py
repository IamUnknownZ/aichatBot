"""Additive anonymous history. Inject ``store._connect``; no live DB on import.

Tokens are bearer capabilities: create with new_browser_token(), keep in browser
storage, and never use display names for lookup. Reads/schema/profile writes raise
HistoryUnavailable on storage failure. Exchange saves and deletes return False.
initialize() is explicit and must be authorized before applying to a live DB.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import math
from pathlib import Path
import re
import secrets
from uuid import UUID, uuid4

PERSONA_IDS = frozenset(('nui', 'saimai', 'bam', 'bas', 'kaka', 'sabaitae'))
MAX_BYTES = 2 * 1024 * 1024
MAX_METADATA = 8 * 1024 * 1024
BYTE_TAG = '__history_bytes__'


class HistoryUnavailable(RuntimeError):
    """Storage could not be read or written; never interpret as empty history."""


def new_browser_token() -> str:
    return secrets.token_urlsafe(32)


def _owner(token):
    if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43,128}', token):
        raise ValueError('Invalid browser capability')
    try:
        raw = base64.b64decode(token + '=' * (-len(token) % 4), altchars=b'-_', validate=True)
    except binascii.Error:
        raise ValueError('Invalid browser capability') from None
    if len(raw) < 32 or base64.urlsafe_b64encode(raw).decode().rstrip('=') != token:
        raise ValueError('Invalid browser capability')
    return hashlib.sha256(token.encode('ascii')).hexdigest()


def _persona(persona):
    if not isinstance(persona, str) or persona not in PERSONA_IDS:
        raise ValueError('Unknown AI tutor identity')


def _transform(value, *, decode=False, depth=0):
    if depth > 30:
        raise ValueError('Metadata nesting limit exceeded')
    if isinstance(value, bytes):
        if len(value) > MAX_BYTES:
            raise ValueError('Image preview too large')
        return {BYTE_TAG: base64.b64encode(value).decode('ascii')}
    if isinstance(value, dict):
        if BYTE_TAG in value:
            if not decode or set(value) != {BYTE_TAG} or not isinstance(value[BYTE_TAG], str):
                raise ValueError('Invalid bytes envelope')
            encoded = value[BYTE_TAG]
            if len(encoded) > 4 * ((MAX_BYTES + 2) // 3):
                raise ValueError('Image preview too large')
            try:
                data = base64.b64decode(encoded, validate=True)
            except (ValueError, binascii.Error):
                raise ValueError('Invalid preview base64') from None
            if len(data) > MAX_BYTES or base64.b64encode(data).decode() != encoded:
                raise ValueError('Invalid preview base64')
            return data
        if any(not isinstance(k, str) for k in value):
            raise ValueError('Metadata keys must be strings')
        return {k: _transform(v, decode=decode, depth=depth + 1) for k, v in value.items()}
    if isinstance(value, list):
        return [_transform(v, decode=decode, depth=depth + 1) for v in value]
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise ValueError('Metadata must be JSON safe')


def encode_metadata(metadata) -> str:
    if not isinstance(metadata, dict):
        raise ValueError('Metadata must be an object')
    encoded = json.dumps(_transform(metadata), ensure_ascii=False, allow_nan=False,
                         sort_keys=True, separators=(',', ':'))
    if len(encoded.encode('utf-8')) > MAX_METADATA:
        raise ValueError('Metadata size limit exceeded')
    return encoded


def decode_metadata(encoded) -> dict:
    if not isinstance(encoded, str) or len(encoded.encode('utf-8')) > MAX_METADATA:
        raise ValueError('Invalid metadata size')
    try:
        value = json.loads(encoded)
        if not isinstance(value, dict):
            raise ValueError('Metadata must be an object')
        return _transform(value, decode=True)
    except (RecursionError, json.JSONDecodeError):
        raise ValueError('Invalid metadata') from None


class ChatHistory:
    def __init__(self, connect):
        self._connect = connect

    def initialize(self):
        try:
            schema = (Path(__file__).resolve().parents[1] / 'db/chat_history.sql').read_text()
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(schema)
        except Exception:
            raise HistoryUnavailable('History schema unavailable') from None

    def get_profile(self, token):
        owner = _owner(token)
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute('SELECT display_name FROM browser_chat_owners WHERE token_hash = %s', (owner,))
                    row = cur.fetchone()
            return {'display_name': row[0]} if row else None
        except Exception:
            raise HistoryUnavailable('History profile unavailable') from None

    def set_profile(self, token, name):
        owner = _owner(token)
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 120:
            raise ValueError('Display name must contain 1 to 120 characters')
        name = name.strip()
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute('INSERT INTO browser_chat_owners(token_hash, display_name) VALUES (%s, %s) '
                                'ON CONFLICT(token_hash) DO UPDATE SET display_name = excluded.display_name', (owner, name))
            return {'display_name': name}
        except Exception:
            raise HistoryUnavailable('History profile unavailable') from None

    def load_messages(self, token, persona_id, limit=80):
        owner = _owner(token)
        _persona(persona_id)
        if type(limit) is not int or not 1 <= limit <= 80:
            raise ValueError('History limit must be 1 to 80 messages')
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute('SELECT question, answer, assistant_metadata FROM browser_chat_exchanges '
                                'WHERE owner_hash = %s AND persona_id = %s '
                                'ORDER BY order_id DESC LIMIT %s',
                                (owner, persona_id, (limit + 1) // 2))
                    rows = cur.fetchall()
            messages = []
            for question, answer, metadata in reversed(rows):
                messages.append({'role': 'user', 'content': question})
                messages.append({**decode_metadata(metadata), 'role': 'assistant', 'content': answer})
            return messages[-limit:]
        except Exception:
            raise HistoryUnavailable('History messages unavailable') from None

    def save_exchange(self, token, persona_id, question, answer, assistant_metadata=None, *, exchange_id=None):
        owner = _owner(token)
        _persona(persona_id)
        if not isinstance(question, str) or not isinstance(answer, str):
            raise ValueError('Question and answer must be strings')
        metadata = encode_metadata({} if assistant_metadata is None else assistant_metadata)
        try:
            exchange = str(UUID(str(exchange_id))) if exchange_id is not None else str(uuid4())
        except ValueError:
            raise ValueError('Invalid exchange UUID') from None
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute('INSERT INTO browser_chat_owners(token_hash, display_name) VALUES (%s, %s) '
                                'ON CONFLICT(token_hash) DO NOTHING', (owner, ''))
                    cur.execute('INSERT INTO browser_chat_exchanges '
                                '(owner_hash, persona_id, exchange_id, question, answer, assistant_metadata) '
                                'VALUES (%s, %s, %s, %s, %s, %s) '
                                'ON CONFLICT(owner_hash, persona_id, exchange_id) DO NOTHING',
                                (owner, persona_id, exchange, question, answer, metadata))
                    cur.execute('SELECT question, answer, assistant_metadata FROM browser_chat_exchanges '
                                'WHERE owner_hash = %s AND persona_id = %s AND exchange_id = %s',
                                (owner, persona_id, exchange))
                    row = cur.fetchone()
                    success = row is not None and tuple(row) == (question, answer, metadata)
            return success
        except Exception:
            return False

    def clear_history(self, token, persona_id):
        owner = _owner(token)
        _persona(persona_id)
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute('DELETE FROM browser_chat_exchanges WHERE owner_hash = %s AND persona_id = %s',
                                (owner, persona_id))
            return True
        except Exception:
            return False
