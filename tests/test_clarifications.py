import unittest

from rag.bootstrap import build_rag_service
from rag.clarifications import (
    TOTAL_CLARIFICATION_ALIASES,
    match_clarification,
)
from rag.config import Settings
from rag.models import RetrievalResult


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
            "มีรูปประกอบไหม": "visualize",
            "มีภาพไหม": "visualize",
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

    def test_mixed_visual_topic_query_is_visual_request(self):
        self.assertTrue(self.service.is_visual_request("รูป sort"))
        self.assertTrue(self.service.is_visual_request("ภาพ Bubble Sort"))
        self.assertFalse(self.service.is_visual_request("Bubble Sort คืออะไร"))
        self.assertFalse(self.service.is_visual_request("ขอภาพรวม Bubble Sort"))
        self.assertFalse(self.service.is_visual_request("รูปแบบของ Quick Sort"))

    def test_visual_followup_reuses_previous_user_query(self):
        history = [
            {"role": "user", "content": "อธิบาย Bubble Sort ให้เข้าใจง่าย"},
            {"role": "assistant", "content": "คำอธิบายก่อนหน้า"},
        ]
        query = "มีรูปประกอบไหม"

        self.assertTrue(self.service.is_visual_request(query))
        self.assertIsNone(self.service.direct_response(query, history))
        self.assertEqual(
            self.service._retrieval_query(query, history),
            "อธิบาย Bubble Sort ให้เข้าใจง่าย",
        )

    def test_specific_algorithm_query_reranks_exact_topic_first(self):
        result = self.service.retrieve("insertion sort คืออะไร", [])
        self.assertTrue(result.hits)
        self.assertIn(
            "insertion sort",
            result.hits[0].content.casefold(),
        )
        self.assertGreaterEqual(
            result.hits[0].content.casefold().count("insertion sort"),
            3,
        )

    def test_general_sort_definition_expands_to_definition_search(self):
        query = "การเรียงลำดับข้อมูลคือ"
        retrieval_query = self.service._retrieval_query(query, [])

        self.assertTrue(self.service._is_general_sort_definition(query))
        self.assertIn("Data Sorting", retrieval_query)
        self.assertIn("ความหมาย", retrieval_query)

        result = self.service.retrieve(query, [])
        self.assertTrue(result.hits)
        top_text = " ".join(result.hits[0].content.split())
        self.assertIn("การจัดเรียงข้อมูล", top_text)
        self.assertIn("Data Sorting", top_text)

    def test_grounded_fallback_is_readable_not_raw_chunk_dump(self):
        result = self.service.retrieve("การเรียงลำดับข้อมูลคือ", [])
        fallback = self.service._fast_grounded_fallback(result.hits)

        self.assertNotIn("คำตอบแบบเร็วจากหลักฐาน", fallback)
        self.assertNotIn("อธิบายหลักการเรียงลำดับข้อมูลแบบ Selection Sort ได้", fallback)
        self.assertIn("การเรียงลำดับข้อมูล", fallback)

    def test_general_sort_definition_skips_generation(self):
        query = "การเรียงลำดับข้อมูลคือ"
        result = self.service.retrieve(query, [])
        answer = "".join(
            self.service.stream_answer(
                query=query,
                result=result,
                history=[],
            )
        )

        self.assertIn("Data Sorting", answer)
        self.assertNotIn("คำตอบแบบเร็วจากหลักฐาน", answer)

    def test_insufficient_evidence_stream_has_single_fallback(self):
        result = RetrievalResult(
            query="คำถามนอกฐานความรู้",
            retrieval_query="คำถามนอกฐานความรู้",
            hits=[],
            elapsed_ms=0.0,
        )
        chunks = list(
            self.service.stream_answer(
                query=result.query,
                result=result,
                history=[],
            )
        )

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].count("ผมยังไม่พบข้อมูลที่เพียงพอ"), 1)


if __name__ == "__main__":
    unittest.main()
