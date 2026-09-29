import unittest
import inspect

import prompt
from rag.service import RAGService
from rag.config import Settings
from rag.store import LocalLexicalStore


class PersonaPromptTests(unittest.TestCase):
    def test_selected_identity_does_not_mutate_other_cached_requests(self):
        base = RAGService(settings=Settings(gemini_api_key='test-key'), embedder=None,
                          store=LocalLexicalStore([]))
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
