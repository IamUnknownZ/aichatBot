import unittest

from rag.bootstrap import build_rag_service
from rag.clarifications import (
    TOTAL_CLARIFICATION_ALIASES,
    match_clarification,
)
from rag.config import Settings


class ClarificationDictionaryTests(unittest.TestCase):
    def test_dictionary_has_broad_coverage(self):
        self.assertGreaterEqual(TOTAL_CLARIFICATION_ALIASES, 200)

    def test_general_sort_is_clarified(self):
        for query in ("sort", "sorting", "ซอร์ท", "การเรียง"):
            match = match_clarification(query)
            self.assertIsNotNone(match, query)
            self.assertEqual(match.canonical, "general_sort")

    def test_action_only_queries_are_clarified(self):
        cases = {
            "code": "code",
            "trace": "trace",
            "complexity": "complexity",
            "compare": "compare",
            "ตัวอย่าง": "example",
            "สรุป": "summary",
            "ขอภาพ": "visualize",
            "ข้อดีข้อเสีย": "pros_cons",
        }
        for query, expected in cases.items():
            match = match_clarification(query)
            self.assertIsNotNone(match, query)
            self.assertEqual(match.canonical, expected)

    def test_specific_queries_are_not_clarified(self):
        for query in (
            "Bubble Sort",
            "อธิบาย Bubble Sort",
            "อธิบาย Big-O",
            "Quick Sort Python",
            "Bubble Sort กับ Selection Sort ต่างกันอย่างไร",
        ):
            self.assertIsNone(match_clarification(query), query)


class ClarificationServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service = build_rag_service(
            Settings(gemini_api_key="test-key", database_url="")
        )

    def test_sort_returns_clarification_without_retrieval(self):
        history = []
        direct = self.service.direct_response("sort", history)
        self.assertIsNotNone(direct)
        result = self.service.retrieve("sort", history)
        self.assertEqual(result.retrieval_query, "__conversation__")
        self.assertEqual(result.elapsed_ms, 0.0)

    def test_context_resolves_code_without_reasking_topic(self):
        history = [
            {"role": "user", "content": "Bubble Sort คืออะไร"},
            {"role": "assistant", "content": "คำอธิบายก่อนหน้า"},
        ]
        self.assertIsNone(self.service.direct_response("code", history))
        retrieval_query = self.service._retrieval_query("code", history)
        self.assertIn("Bubble Sort", retrieval_query)
        self.assertIn("code", retrieval_query)

    def test_compare_still_requires_two_targets(self):
        history = [
            {"role": "user", "content": "Bubble Sort คืออะไร"},
            {"role": "assistant", "content": "คำอธิบายก่อนหน้า"},
        ]
        direct = self.service.direct_response("compare", history)
        self.assertIsNotNone(direct)
        self.assertIn("อัลกอริทึมไหน", direct)


if __name__ == "__main__":
    unittest.main()
