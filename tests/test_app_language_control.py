import os
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


class AppLanguageControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._saved_env = {
            name: os.environ.get(name)
            for name in ("PROFILE_ENABLED", "GEMINI_API_KEY", "DATABASE_URL")
        }
        os.environ["PROFILE_ENABLED"] = "false"
        os.environ["GEMINI_API_KEY"] = ""
        os.environ["DATABASE_URL"] = ""
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        cls.app = AppTest.from_file(str(app_path))
        cls.app.run(timeout=60)

    @classmethod
    def tearDownClass(cls):
        for name, value in cls._saved_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    def test_language_control_floats_with_the_original_chat_input(self):
        self.assertFalse(self.app.exception)
        self.assertEqual(len(self.app.segmented_control), 1)
        self.assertEqual(
            self.app.segmented_control[0].options,
            ["ไทย / Thai", "English / อังกฤษ"],
        )
        self.assertEqual(len(self.app.chat_input), 1)
        self.assertEqual(len(self.app.text_input), 0)
        send_buttons = [button for button in self.app.button if button.label == "ส่ง"]
        self.assertEqual(len(send_buttons), 0)
        self.assertEqual(len(self.app.selectbox), 0)
        self.assertTrue(
            any(
                "language-float" in item.value
                for item in self.app.markdown
            )
        )

    def test_language_control_updates_the_next_answer_mode(self):
        for label, expected in (
            ("ไทย / Thai", "thai"),
            ("English / อังกฤษ", "english"),
        ):
            self.app.segmented_control[0].set_value(label)
            self.app.run(timeout=60)
            self.assertFalse(self.app.exception)
            self.assertEqual(self.app.segmented_control[0].value, label)
            self.assertEqual(self.app.session_state["response_language"], expected)

    def test_language_float_prevents_segmented_control_wrapping(self):
        theme_css = (
            Path(__file__).resolve().parents[1] / "ui" / "theme.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            'div[class*="st-key-language-float"] > '
            '[data-testid="stElementContainer"]',
            theme_css,
        )
        self.assertIn(
            'div[class*="st-key-language-float"] [role="radiogroup"]',
            theme_css,
        )
        self.assertIn("flex-wrap: nowrap !important;", theme_css)
        self.assertIn("width: max-content !important;", theme_css)

    def test_composer_reserves_clear_space_for_language_switch_on_desktop(self):
        theme_css = (
            Path(__file__).resolve().parents[1] / "ui" / "theme.py"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "width: min(620px, calc(100vw - 1.5rem - 453px)) !important;",
            theme_css,
        )
        self.assertIn(
            "width: min(600px, calc(100vw - 310px)) !important;",
            theme_css,
        )


if __name__ == "__main__":
    unittest.main()
