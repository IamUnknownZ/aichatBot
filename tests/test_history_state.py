import unittest
import importlib.util
from pathlib import Path
from rag.chat_history import new_browser_token, HistoryUnavailable


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
