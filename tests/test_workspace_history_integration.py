from contextlib import contextmanager
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from rag.chat_history import new_browser_token
from rag.config import Settings
from rag.service import RAGService
from rag.store import PgVectorStore
from tests.test_chat_history import Connection


class WorkspaceFailureTests(unittest.TestCase):
    def test_retrieval_exception_never_exposes_connection_details(self):
        database = sqlite3.connect(':memory:', check_same_thread=False)
        self.addCleanup(database.close)
        @contextmanager
        def connect():
            with database:
                yield Connection(database)
        store = PgVectorStore('qa-test')
        store._connect = connect
        service = RAGService(settings=Settings(gemini_api_key='qa-test-key', profile_enabled=False),
                             embedder=None, store=store)
        env = {'GEMINI_API_KEY': 'qa-test-key', 'DATABASE_URL': '', 'PROFILE_ENABLED': 'false'}
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'))
        app.session_state['browser_identity'] = {'token': new_browser_token(), 'persisted': True}
        with patch.dict('os.environ', env), \
             patch('rag.bootstrap.build_rag_service', return_value=service), \
             patch.object(RAGService, 'retrieve', side_effect=RuntimeError('postgres://credential_secret@host')):
            app.run()
            self.assertFalse(app.exception)
            app.chat_input[0].set_value('Bubble Sort').run()
        self.assertFalse(app.exception)
        self.assertTrue(app.error)
        visible = '\n'.join([m.value for m in app.markdown] + [e.value for e in app.error])
        self.assertNotIn('credential_secret', visible)
        self.assertNotIn('postgres://', visible)
        self.assertNotIn('credential_secret', str(app.session_state['messages']))
