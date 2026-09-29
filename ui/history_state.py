from rag.chat_history import _owner, HistoryUnavailable


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
