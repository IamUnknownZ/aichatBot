import unittest
import os
from pathlib import Path
from unittest.mock import patch
from rag.personas import get_persona
from ui.workspace import persona_avatar
from streamlit.testing.v1 import AppTest


class WorkspaceTests(unittest.TestCase):
    def test_placeholder_avatar_still_renders_when_cloud_font_is_missing(self):
        with patch('ui.workspace.ImageFont.truetype', side_effect=OSError('font unavailable')):
            try:
                avatar = persona_avatar(get_persona('nui'))
            except OSError:
                self.fail('Missing system fonts must not prevent the chat workspace opening')
        self.assertTrue(avatar.startswith(b'\x89PNG'))

    def test_sidebar_selects_six_tutors_in_order_and_preserves_separate_threads(self):
        with patch.dict(os.environ, {'GEMINI_API_KEY': '', 'DATABASE_URL': '', 'PROFILE_ENABLED': 'false'}):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run(timeout=60)
            self.assertFalse(app.exception)
            tutors = [b for b in app.sidebar.button if b.key and b.key.startswith('persona_')]
            self.assertEqual([b.key for b in tutors], ['persona_nui','persona_saimai','persona_bam','persona_bas','persona_kaka','persona_sabaitae'])
            app.session_state['messages'].append({'role':'user','content':'Nui-only question'})
            tutors[1].click().run(timeout=60)
            self.assertEqual(app.session_state['active_persona'], 'saimai')
            self.assertFalse(any(m['content']=='Nui-only question' for m in app.session_state['messages']))
            app.button(key='persona_nui').click().run(timeout=60)
            self.assertTrue(any(m['content']=='Nui-only question' for m in app.session_state['messages']))


if __name__ == '__main__': unittest.main()
