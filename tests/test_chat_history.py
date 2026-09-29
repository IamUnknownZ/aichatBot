"""Behavior tests using real SQLite transactions; PostgreSQL integration NOT_RUN.

The adapter changes parameter syntax and identity DDL to SQLite's equivalent.
It does not emulate query results.
"""
from contextlib import contextmanager
import hashlib
import importlib
from pathlib import Path
import secrets
import sqlite3
import unittest


class Cursor:
    def __init__(self, conn):
        self.cursor = conn.cursor()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.cursor.close()

    def execute(self, sql, params=None):
        if params is None:
            for statement in sql.split(';'):
                if statement.strip():
                    # SQLite has no RLS. Policy enforcement needs PostgreSQL
                    # integration and is not claimed by these transaction tests.
                    if 'ENABLE ROW LEVEL SECURITY' in statement:
                        continue
                    statement = statement.replace(
                        'order_id BIGINT GENERATED ALWAYS AS IDENTITY UNIQUE',
                        'order_id INTEGER PRIMARY KEY AUTOINCREMENT').replace(
                        'PRIMARY KEY (owner_hash, persona_id, exchange_id)',
                        'UNIQUE (owner_hash, persona_id, exchange_id)')
                    self.cursor.execute(statement)
        else:
            self.cursor.execute(sql.replace('%s', '?'), params)

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchall(self):
        return self.cursor.fetchall()


class Connection:
    def __init__(self, conn):
        self.conn = conn

    def cursor(self):
        return Cursor(self.conn)


class HistoryTests(unittest.TestCase):
    def setUp(self):
        # Missing backend is an explicit assertion failure during RED.
        path = Path(__file__).resolve().parents[1] / 'rag/chat_history.py'
        self.assertTrue(path.exists(), 'history backend is not implemented')
        spec = importlib.util.spec_from_file_location('history_backend', path)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.db = sqlite3.connect(':memory:')
        self.addCleanup(self.db.close)

        @contextmanager
        def connect():
            with self.db:
                yield Connection(self.db)

        self.history = self.module.ChatHistory(connect)
        self.history.initialize()
        self.a, self.b = secrets.token_urlsafe(32), secrets.token_urlsafe(32)

    def test_same_names_do_not_merge_and_token_is_hashed(self):
        for token in (self.a, self.b):
            self.assertEqual(self.history.set_profile(token, '  Alex  '), {'display_name': 'Alex'})
        self.assertTrue(self.history.save_exchange(self.a, 'nui', 'q', 'a', {}))
        self.assertEqual(self.history.load_messages(self.b, 'nui'), [])
        self.assertIsNone(self.history.get_profile(secrets.token_urlsafe(32)))
        self.assertEqual(self.history.get_profile(self.a), {'display_name': 'Alex'})
        dump = '\n'.join(self.db.iterdump())
        self.assertNotIn(self.a, dump)
        self.assertIn(hashlib.sha256(self.a.encode()).hexdigest(), dump)
        self.history.set_profile(self.a, 'New name')
        self.assertEqual(len(self.history.load_messages(self.a, 'nui')), 2)

    def test_roundtrip_metadata_and_bytes_with_protected_role_content(self):
        metadata = {'sources': [{'source_id': 'lecture', 'page': 2}],
                    'images': [{'image_bytes': b'\x89PNG\x00', 'source_id': 'lecture'}],
                    'visual_request': True, 'answered': True,
                    'role': 'user', 'content': 'injected'}
        self.assertTrue(self.history.save_exchange(self.a, 'bas', 'question', 'answer', metadata))
        messages = self.history.load_messages(self.a, 'bas')
        self.assertEqual(messages[0], {'role': 'user', 'content': 'question'})
        self.assertEqual(messages[1]['role'], 'assistant')
        self.assertEqual(messages[1]['content'], 'answer')
        self.assertEqual(messages[1]['images'], metadata['images'])
        self.assertEqual(messages[1]['sources'], metadata['sources'])
        self.assertTrue(messages[1]['visual_request'])

    def test_latest_bounded_messages_in_chronological_order(self):
        for i in range(43):
            self.assertTrue(self.history.save_exchange(self.a, 'nui', f'q{i}', f'a{i}', {}))
        self.assertEqual(len(self.history.load_messages(self.a, 'nui')), 80)
        self.assertEqual([m['content'] for m in self.history.load_messages(self.a, 'nui', limit=3)],
                         ['a41', 'q42', 'a42'])

    def test_clear_is_owner_and_persona_scoped(self):
        for token, persona in [(self.a, 'nui'), (self.a, 'bas'), (self.b, 'nui')]:
            self.history.save_exchange(token, persona, 'q', 'a', {})
        self.assertTrue(self.history.clear_history(self.a, 'nui'))
        self.assertEqual(self.history.load_messages(self.a, 'nui'), [])
        self.assertEqual(len(self.history.load_messages(self.a, 'bas')), 2)
        self.assertEqual(len(self.history.load_messages(self.b, 'nui')), 2)

    def test_exchange_retry_is_idempotent_but_conflict_fails(self):
        exchange = '12345678-1234-4234-8234-123456789abc'
        for _ in range(2):
            self.assertTrue(self.history.save_exchange(self.a, 'nui', 'q', 'a', {}, exchange_id=exchange))
        self.assertFalse(self.history.save_exchange(self.a, 'nui', 'different', 'a', {}, exchange_id=exchange))
        self.assertEqual(len(self.history.load_messages(self.a, 'nui')), 2)
        self.assertTrue(self.history.save_exchange(self.b, 'nui', 'q', 'a', {}, exchange_id=exchange))

    def test_invalid_inputs_rejected(self):
        for token in ('Alex', '', 'a' * 42, '! ' * 40):
            with self.assertRaises(ValueError):
                self.history.get_profile(token)
        for persona in ('Nui', 'unknown', ''):
            with self.assertRaises(ValueError):
                self.history.load_messages(self.a, persona)
        for limit in (0, -1, 81, True):
            with self.assertRaises(ValueError):
                self.history.load_messages(self.a, 'nui', limit)
        for name in ('', ' ' * 3, 'a' * 121):
            with self.assertRaises(ValueError):
                self.history.set_profile(self.a, name)

    def test_serialization_rejects_malformed_and_oversized_bytes(self):
        with self.assertRaises(ValueError):
            self.module.decode_metadata('{"images":[{"__history_bytes__":"@@@"}]}')
        with self.assertRaises(ValueError):
            self.module.encode_metadata({'images': [b'x' * (2 * 1024 * 1024 + 1)]})
        with self.assertRaises(ValueError):
            self.module.decode_metadata('{"sources":NaN}')
        with self.assertRaises(ValueError):
            self.module.encode_metadata({'sources': object()})

    def test_database_failures_are_explicit_and_atomic(self):
        self.db.execute("CREATE TRIGGER reject_exchange BEFORE INSERT ON browser_chat_exchanges BEGIN SELECT RAISE(ABORT, 'failure'); END")
        self.assertFalse(self.history.save_exchange(self.a, 'nui', 'q', 'a', {}))
        self.assertEqual(self.history.load_messages(self.a, 'nui'), [])
        self.assertIsNone(self.history.get_profile(self.a))
        self.db.close()
        self.assertFalse(self.history.save_exchange(self.a, 'nui', 'q', 'a', {}))
        self.assertFalse(self.history.clear_history(self.a, 'nui'))
        with self.assertRaises(self.module.HistoryUnavailable):
            self.history.load_messages(self.a, 'nui')
        with self.assertRaises(self.module.HistoryUnavailable):
            self.history.get_profile(self.a)
        with self.assertRaises(self.module.HistoryUnavailable):
            self.history.set_profile(self.a, 'Alex')
        with self.assertRaises(self.module.HistoryUnavailable):
            self.history.initialize()

    def test_corrupt_persisted_preview_fails_closed(self):
        self.history.save_exchange(self.a, 'nui', 'q', 'a', {})
        self.db.execute('UPDATE browser_chat_exchanges SET assistant_metadata = ?',
                        ('{"images":[{"__history_bytes__":"@@@"}]}',))
        with self.assertRaises(self.module.HistoryUnavailable):
            self.history.load_messages(self.a, 'nui')

    def test_generated_capabilities_work_without_profile_setup(self):
        token = self.module.new_browser_token()
        self.assertGreaterEqual(len(__import__('base64').urlsafe_b64decode(token + '=')), 32)
        self.assertTrue(self.history.save_exchange(token, 'sabaitae', 'q', 'a'))
        self.assertEqual(self.history.load_messages(token, 'sabaitae')[1]['content'], 'a')
        self.history.initialize()
        self.assertEqual(len(self.history.load_messages(token, 'sabaitae')), 2)

    def test_serialization_limits_whole_payload_and_nesting(self):
        with self.assertRaises(ValueError):
            self.module.encode_metadata({'sources': 'x' * (8 * 1024 * 1024)})
        nested = {}
        for _ in range(32):
            nested = {'child': nested}
        with self.assertRaises(ValueError):
            self.module.encode_metadata(nested)

    def test_idempotency_is_also_persona_scoped(self):
        exchange = '12345678-1234-4234-8234-123456789abc'
        for persona in ('nui', 'bas'):
            self.assertTrue(self.history.save_exchange(self.a, persona, 'q', 'a', {}, exchange_id=exchange))
            self.assertEqual(len(self.history.load_messages(self.a, persona)), 2)


if __name__ == '__main__':
    unittest.main()
