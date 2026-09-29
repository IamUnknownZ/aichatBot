import unittest

# Import before AppTest creates a runtime. Component registration must still
# happen in the active runtime when browser_identity() is called by the app.
from ui.browser_identity import browser_identity  # noqa: F401

from streamlit.testing.v1 import AppTest


APP_SOURCE = """
from ui.browser_identity import browser_identity
browser_identity()
"""


class BrowserIdentityRuntimeTests(unittest.TestCase):
    def test_truthy_string_cannot_claim_persistent_identity(self):
        import ui.browser_identity as module
        from rag.chat_history import new_browser_token
        normalize = getattr(module, 'normalize_identity', None)
        token = new_browser_token()
        self.assertTrue(callable(normalize), 'Component data must be validated before use')
        self.assertEqual(normalize({'token': token, 'persisted': 'false', 'extra': 'ignored'}),
                         {'token': token, 'persisted': False})
        self.assertTrue(normalize({'token': token, 'persisted': True})['persisted'])

    def test_component_registers_for_sequential_apptest_runtimes(self):
        for _ in range(2):
            app = AppTest.from_string(APP_SOURCE).run()
            self.assertFalse(app.exception, "browser identity must mount in each AppTest runtime")


if __name__ == "__main__":
    unittest.main()
