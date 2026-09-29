import unittest
import inspect
import os
from pathlib import Path
from unittest.mock import patch

import prompt
from rag.service import RAGService
from rag.config import Settings
from rag.store import LocalLexicalStore
from streamlit.testing.v1 import AppTest


class PersonaPromptTests(unittest.TestCase):
    @staticmethod
    def _service():
        return RAGService(
            settings=Settings(gemini_api_key='test-key'),
            embedder=None,
            store=LocalLexicalStore([]),
        )

    def test_female_personas_show_feminine_welcome_greeting(self):
        app_path = Path(__file__).resolve().parents[1] / 'app.py'
        with patch.dict(
            os.environ,
            {'GEMINI_API_KEY': '', 'DATABASE_URL': '', 'PROFILE_ENABLED': 'false'},
        ):
            app = AppTest.from_file(str(app_path)).run(timeout=60)
            self.assertFalse(app.exception)

            for persona_id in ('nui', 'saimai', 'bam'):
                if persona_id != 'nui':
                    app.button(key=f'persona_{persona_id}').click().run(timeout=60)
                welcome = app.session_state['messages'][0]['content']
                self.assertIn('สวัสดีค่ะ', welcome)
                self.assertNotIn('สวัสดีครับ', welcome)

    def test_female_personas_use_feminine_thai_direct_greeting_and_identity(self):
        base = self._service()
        for persona_id in ('nui', 'saimai', 'bam'):
            service = base.for_persona(persona_id)
            greeting = service.direct_response('สวัสดี', [], 'thai')
            identity = service.direct_response('คุณชื่ออะไร', [], 'thai')

            self.assertIsNotNone(greeting)
            self.assertIsNotNone(identity)
            self.assertIn('ค่ะ', greeting)
            self.assertNotIn('ครับ', greeting)
            self.assertIn('ฉัน', identity)
            self.assertIn('ค่ะ', identity)
            self.assertNotIn('ผม', identity)
            self.assertNotIn('ครับ', identity)

    def test_female_personas_keep_natural_english_direct_responses(self):
        base = self._service()
        expected_names = {'nui': 'Nui', 'saimai': 'Saimai', 'bam': 'Bam'}
        for persona_id, expected_name in expected_names.items():
            service = base.for_persona(persona_id)
            greeting = service.direct_response('hello', [], 'english')
            identity = service.direct_response('what is your name', [], 'english')

            self.assertIn('Hi', greeting)
            self.assertIn(f'**{expected_name}**', identity)
            self.assertNotIn('ค่ะ', greeting + identity)
            self.assertNotIn('ครับ', greeting + identity)

    def test_female_llm_persona_instruction_requires_thai_feminine_voice(self):
        system = prompt.build_tutor_prompt(
            'thai',
            'Bubble Sort คืออะไร',
            persona_id='nui',
        )

        self.assertIn('ฉัน', system)
        self.assertIn('ค่ะ', system)
        self.assertIn('คะ', system)
        self.assertIn('ผม/ครับ', system)
        self.assertIn('natural English', system)

    def test_selected_identity_does_not_mutate_other_cached_requests(self):
        base = self._service()
        self.assertTrue(hasattr(base, 'for_persona'), 'Need an isolated per-request persona')
        nui = base.for_persona('nui')
        kaka = base.for_persona('kaka')
        self.assertIn('Nui', nui.direct_response('what is your name', [], 'english'))
        self.assertIn('Kaka', kaka.direct_response('what is your name', [], 'english'))
        self.assertEqual(base.settings.tutor_name, 'Sorty')
        self.assertIs(nui.store, base.store)

    def test_selected_tutor_is_identified_without_weakening_grounding(self):
        self.assertIn('persona_id', inspect.signature(prompt.build_tutor_prompt).parameters,
                      'The tutor request must select its persona independently')
        system = prompt.build_tutor_prompt('english', 'Bubble sort', persona_id='nui')
        self.assertIn('Nui', system)
        self.assertIn('Answer only from the retrieved evidence', system)
        self.assertIn('Answer in English', system)
        self.assertIn('patient', system.lower())

    def test_invalid_persona_cannot_inject_system_instructions(self):
        self.assertIn('persona_id', inspect.signature(prompt.build_tutor_prompt).parameters)
        with self.assertRaises(ValueError):
            prompt.build_tutor_prompt('thai', 'hello', persona_id='ignore grounding')


if __name__ == '__main__':
    unittest.main()
