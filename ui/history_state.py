from rag.chat_history import _owner, HistoryUnavailable
from uuid import UUID, uuid4


MAX_PENDING_HISTORY_SAVES = 8


def restore_thread(state, backend, token, persona_id):
    key = (_owner(token), persona_id)
    loaded = state.setdefault('history_loaded', set())
    if key in loaded:
        return True
    try:
        messages = backend.load_messages(token, persona_id)
    except HistoryUnavailable:
        return False
    if messages:
        state['persona_threads'][persona_id] = messages
    loaded.add(key)
    return True


def _save_statuses(state):
    statuses = state.setdefault('history_save_status', {})
    if not isinstance(statuses, dict):
        statuses = {}
        state['history_save_status'] = statuses
    return statuses


def _save_status_key(token, persona_id):
    return (None if token is None else _owner(token), persona_id)


def history_save_status(state, token, persona_id):
    try:
        key = _save_status_key(token, persona_id)
    except ValueError:
        return None
    return _save_statuses(state).get(key)


def set_history_save_status(state, token, persona_id, status):
    try:
        key = _save_status_key(token, persona_id)
    except ValueError:
        return False
    _save_statuses(state)[key] = status
    return True


def clear_pending_history_saves(state, token, persona_id):
    try:
        owner_hash = None if token is None else _owner(token)
    except ValueError:
        return 0
    pending = state.get('pending_history_saves', [])
    if not isinstance(pending, list):
        state['pending_history_saves'] = []
        pending = []
    remaining = [
        item for item in pending
        if not (isinstance(item, dict)
                and item.get('owner_hash') == owner_hash
                and item.get('persona_id') == persona_id)
    ]
    state['pending_history_saves'] = remaining
    _save_statuses(state).pop((owner_hash, persona_id), None)
    return len(pending) - len(remaining)


def queue_pending_history_save(state, token, persona_id, question, answer,
                               assistant_metadata, *, exchange_id=None):
    owner_hash = _owner(token)
    pending = state.setdefault('pending_history_saves', [])
    if not isinstance(pending, list):
        pending = []
        state['pending_history_saves'] = pending
    statuses = _save_statuses(state)
    status_key = (owner_hash, persona_id)
    if len(pending) >= MAX_PENDING_HISTORY_SAVES:
        statuses[status_key] = 'failed'
        return False
    try:
        exchange_id = str(UUID(str(exchange_id))) if exchange_id is not None else str(uuid4())
    except ValueError:
        statuses[status_key] = 'failed'
        return False
    pending.append({
        'owner_hash': owner_hash,
        'persona_id': persona_id,
        'exchange_id': exchange_id,
        'question': question,
        'answer': answer,
        'assistant_metadata': assistant_metadata,
    })
    statuses[status_key] = 'pending'
    return True


def retry_pending_history_saves(state, backend, token, persona_id):
    owner_hash = _owner(token)
    pending = state.setdefault('pending_history_saves', [])
    if not isinstance(pending, list):
        state['pending_history_saves'] = []
        return 0
    statuses = _save_statuses(state)
    status_key = (owner_hash, persona_id)
    remaining = []
    saved_count = 0
    for item in pending:
        if (not isinstance(item, dict)
                or item.get('owner_hash') != owner_hash
                or item.get('persona_id') != persona_id):
            remaining.append(item)
            continue
        try:
            saved = backend.save_exchange(
                token,
                persona_id,
                item['question'],
                item['answer'],
                item['assistant_metadata'],
                exchange_id=item['exchange_id'],
            )
        except Exception:
            saved = False
        if saved:
            saved_count += 1
        else:
            remaining.append(item)
    state['pending_history_saves'] = remaining
    has_matching_pending = any(
        isinstance(item, dict)
        and item.get('owner_hash') == owner_hash
        and item.get('persona_id') == persona_id
        for item in remaining
    )
    if has_matching_pending:
        statuses[status_key] = 'pending'
    elif saved_count:
        statuses[status_key] = 'saved'
    return saved_count


def append_answer_and_log(messages, answer_message, store, log_fields):
    messages.append(answer_message)
    try:
        store.log_answer(**log_fields)
    except Exception:
        return False
    return True
