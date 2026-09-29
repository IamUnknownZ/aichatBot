import unittest
import importlib.util
from pathlib import Path
from rag.chat_history import new_browser_token, HistoryUnavailable, _owner


class HistoryStateTests(unittest.TestCase):
    def test_restore_happens_once_and_persona_threads_stay_separate(self):
        path=Path(__file__).resolve().parents[1]/'ui/history_state.py'
        self.assertTrue(path.exists(), 'Persisted exchanges must reload into the active thread')
        spec=importlib.util.spec_from_file_location('history_state',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        class Backend:
            def load_messages(self, token, persona):
                return [{'role':'user','content':persona+' history'}]
        state={'persona_threads':{'nui':[],'bas':[]}}
        token=new_browser_token()
        self.assertTrue(module.restore_thread(state,Backend(),token,'nui'))
        state['persona_threads']['nui'].append({'role':'assistant','content':'unsaved'})
        module.restore_thread(state,Backend(),token,'nui')
        self.assertEqual(len(state['persona_threads']['nui']),2)
        module.restore_thread(state,Backend(),token,'bas')
        self.assertEqual(state['persona_threads']['bas'][0]['content'],'bas history')

    def test_failed_reload_never_claims_empty_history_or_allows_save(self):
        path=Path(__file__).resolve().parents[1]/'ui/history_state.py'
        self.assertTrue(path.exists())
        spec=importlib.util.spec_from_file_location('history_state',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        class Backend:
            def load_messages(self,*args): raise HistoryUnavailable('offline')
        state={'persona_threads':{'nui':[{'role':'assistant','content':'welcome'}]}}
        self.assertFalse(module.restore_thread(state,Backend(),new_browser_token(),'nui'))
        self.assertEqual(state['persona_threads']['nui'][0]['content'],'welcome')
        self.assertFalse(state.get('history_loaded'))

    def test_pending_save_retry_is_owner_persona_scoped_and_reuses_exchange_id(self):
        path = Path(__file__).resolve().parents[1] / 'ui/history_state.py'
        spec = importlib.util.spec_from_file_location('history_state', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        queue = getattr(module, 'queue_pending_history_save', None)
        retry = getattr(module, 'retry_pending_history_saves', None)

        owner_token = new_browser_token()
        other_token = new_browser_token()
        exchange_id = '12345678-1234-4234-8234-123456789abc'
        metadata = {
            'sources': [{'source_id': 'lecture-1', 'page_number': 3}],
            'images': [{'image_bytes': b'preview-bytes'}],
            'visual_request': True,
        }
        state = {}

        class Backend:
            def __init__(self):
                self.calls = []
                self.outcomes = [False, True]

            def save_exchange(self, token, persona, question, answer, assistant_metadata,
                              *, exchange_id=None):
                self.calls.append((token, persona, question, answer, assistant_metadata, exchange_id))
                return self.outcomes.pop(0)

        backend = Backend()
        if callable(queue) and callable(retry):
            queue(state, owner_token, 'nui', 'question', 'answer', metadata,
                  exchange_id=exchange_id)
            retry(state, backend, other_token, 'nui')
            retry(state, backend, owner_token, 'bas')
            retry(state, backend, owner_token, 'nui')
            retry(state, backend, owner_token, 'nui')

        expected_call = (owner_token, 'nui', 'question', 'answer', metadata, exchange_id)
        self.assertEqual(backend.calls, [expected_call, expected_call])
        self.assertEqual(
            state['history_save_status'][(_owner(owner_token), 'nui')], 'saved'
        )
        self.assertEqual(state.get('pending_history_saves'), [])

    def test_pending_history_outbox_has_a_fixed_session_bound(self):
        path = Path(__file__).resolve().parents[1] / 'ui/history_state.py'
        spec = importlib.util.spec_from_file_location('history_state', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        queue = getattr(module, 'queue_pending_history_save', None)
        token = new_browser_token()
        state = {}
        if callable(queue):
            for index in range(20):
                queue(state, token, 'nui', f'q{index}', f'a{index}', {})

        pending = state.get('pending_history_saves', [])
        self.assertEqual(len(pending), 8)
        self.assertEqual(
            state['history_save_status'][(_owner(token), 'nui')], 'failed'
        )

    def test_partial_persona_save_remains_pending_until_all_matching_items_save(self):
        path = Path(__file__).resolve().parents[1] / 'ui/history_state.py'
        spec = importlib.util.spec_from_file_location('history_state', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        token = new_browser_token()
        state = {}
        module.queue_pending_history_save(
            state, token, 'nui', 'q1', 'a1', {},
            exchange_id='12345678-1234-4234-8234-123456789abc',
        )
        module.queue_pending_history_save(
            state, token, 'nui', 'q2', 'a2', {},
            exchange_id='22345678-1234-4234-8234-123456789abc',
        )

        class Backend:
            def __init__(self):
                self.outcomes = [True, False, True]

            def save_exchange(self, *args, **kwargs):
                return self.outcomes.pop(0)

        backend = Backend()
        module.retry_pending_history_saves(state, backend, token, 'nui')
        self.assertEqual(
            state['history_save_status'][(_owner(token), 'nui')], 'pending'
        )
        self.assertEqual(len(state['pending_history_saves']), 1)

        module.retry_pending_history_saves(state, backend, token, 'nui')
        self.assertEqual(
            state['history_save_status'][(_owner(token), 'nui')], 'saved'
        )
        self.assertEqual(state['pending_history_saves'], [])

    def test_confirmed_persona_clear_removes_only_matching_pending_saves_and_status(self):
        path = Path(__file__).resolve().parents[1] / 'ui/history_state.py'
        spec = importlib.util.spec_from_file_location('history_state', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        clear_pending = getattr(module, 'clear_pending_history_saves', None)
        owner_token = new_browser_token()
        other_token = new_browser_token()
        state = {}
        for token, persona, question in (
            (owner_token, 'nui', 'delete this'),
            (owner_token, 'bas', 'keep this persona'),
            (other_token, 'nui', 'keep this owner'),
        ):
            module.queue_pending_history_save(state, token, persona, question, 'answer', {})
        target_key = (_owner(owner_token), 'nui')
        other_keys = {(_owner(owner_token), 'bas'), (_owner(other_token), 'nui')}

        if callable(clear_pending):
            clear_pending(state, owner_token, 'nui')

        self.assertEqual(
            {(item['owner_hash'], item['persona_id'])
             for item in state['pending_history_saves']},
            other_keys,
        )
        self.assertNotIn(target_key, state['history_save_status'])
        self.assertEqual(set(state['history_save_status']), other_keys)

    def test_session_only_save_status_is_available_without_persistent_identity(self):
        path = Path(__file__).resolve().parents[1] / 'ui/history_state.py'
        spec = importlib.util.spec_from_file_location('history_state', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        set_status = getattr(module, 'set_history_save_status', None)
        state = {}
        if callable(set_status):
            set_status(state, None, 'nui', 'session_only')

        self.assertEqual(
            module.history_save_status(state, None, 'nui'), 'session_only'
        )

    def test_metrics_logging_failure_keeps_completed_answer_visible(self):
        path = Path(__file__).resolve().parents[1] / 'ui/history_state.py'
        spec = importlib.util.spec_from_file_location('history_state', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        append_and_log = getattr(module, 'append_answer_and_log', None)
        answer = {
            'role': 'assistant',
            'content': 'completed answer',
            'sources': [{'source_id': 'lecture-1', 'page_number': 3}],
            'images': [{'image_bytes': b'preview-bytes'}],
        }
        log_fields = {'query': 'question', 'answer_chars': 16}
        messages = []

        class Store:
            def __init__(self):
                self.calls = []

            def log_answer(self, **kwargs):
                self.calls.append(kwargs)
                raise RuntimeError('metrics storage unavailable')

        store = Store()
        result = append_and_log(messages, answer, store, log_fields) if callable(append_and_log) else None

        self.assertFalse(result)
        self.assertEqual(messages, [answer])
        self.assertEqual(store.calls, [log_fields])
