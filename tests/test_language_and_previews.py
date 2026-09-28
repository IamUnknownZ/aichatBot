import unittest
from types import SimpleNamespace

import prompt
from prompt import build_tutor_prompt, resolve_response_language
from rag.config import Settings
from rag.models import RetrievalResult, SearchHit
from rag.service import RAGService
from rag.visuals import compact_image_caption, image_preview_groups


class LanguageModeTests(unittest.TestCase):
    def test_response_language_options_are_bilingual_and_ordered_for_input(self):
        self.assertEqual(
            (
                prompt.response_language_options()
                if hasattr(prompt, "response_language_options")
                else None
            ),
            [
                ("ไทย / Thai", "thai"),
                ("English / อังกฤษ", "english"),
            ],
        )

    def test_response_language_can_be_selected_or_inferred(self):
        self.assertEqual(resolve_response_language("thai", "Explain Bubble Sort"), "th")
        self.assertEqual(resolve_response_language("english", "อธิบาย Bubble Sort"), "en")
        self.assertEqual(resolve_response_language("auto", "อธิบาย Bubble Sort"), "th")
        self.assertEqual(resolve_response_language("auto", "Explain Bubble Sort"), "en")

    def test_prompt_contains_explicit_language_contract(self):
        thai_prompt = build_tutor_prompt("thai", "Explain Bubble Sort")
        english_prompt = build_tutor_prompt("english", "อธิบาย Bubble Sort")
        auto_prompt = build_tutor_prompt("auto", "Explain Bubble Sort")

        self.assertIn("ตอบเป็นภาษาไทย", thai_prompt)
        self.assertIn("Answer in English", english_prompt)
        self.assertIn("ภาษาของคำถาม", auto_prompt)
        self.assertIn("ห้ามคัดลอกข้อความภาษาอังกฤษ", thai_prompt)
        self.assertIn("แปลหรือเรียบเรียง", thai_prompt)
        self.assertIn("translate or paraphrase", english_prompt)
        self.assertIn("6 หัวข้อเท่านั้น", thai_prompt)
        self.assertIn("6 primary topics", english_prompt)

    def test_thai_fallback_explains_english_evidence_instead_of_failing(self):
        service = object.__new__(RAGService)
        service.settings = Settings(gemini_api_key="test-key")
        hit = SearchHit(
            source_id="source",
            source_file="counting sort.pdf",
            page_number=1,
            chunk_index=0,
            content=(
                "Counting sort is an algorithm that sorts an array in O(n + k) time."
            ),
            score=0.9,
            vector_score=0.9,
            lexical_score=0.9,
        )

        fallback = service._fast_grounded_fallback(
            "counting sort คืออะไร",
            [hit],
            "thai",
        )

        self.assertNotIn("ไม่สามารถสร้างคำตอบภาษาไทย", fallback)
        self.assertIn("Counting Sort", fallback)
        self.assertIn("หลักฐานในเอกสารเป็นภาษาอังกฤษ", fallback)
        self.assertIn("Counting sort is an algorithm", fallback)

    def test_thai_comparison_fallback_keeps_all_topics_with_english_evidence(self):
        service = object.__new__(RAGService)
        service.settings = Settings(gemini_api_key="test-key")
        hits = [
            SearchHit(
                source_id="bubble",
                source_file="bubble sort.pdf",
                page_number=4,
                chunk_index=0,
                content=(
                    "Bubble sort repeatedly compares adjacent elements and swaps "
                    "them when they are in the wrong order."
                ),
                score=0.9,
                vector_score=0.9,
                lexical_score=0.9,
                metadata={"section": "bubble_sort"},
            ),
            SearchHit(
                source_id="selection",
                source_file="selection sort.pdf",
                page_number=6,
                chunk_index=0,
                content=(
                    "Selection sort repeatedly selects the smallest remaining "
                    "element and places it in the next position."
                ),
                score=0.88,
                vector_score=0.88,
                lexical_score=0.88,
                metadata={"section": "selection_sort"},
            ),
        ]

        fallback = service._fast_grounded_fallback(
            "Bubble Sort กับ Selection Sort ต่างกันอย่างไร",
            hits,
            "thai",
        )

        self.assertNotIn("ไม่สามารถสร้างคำตอบภาษาไทยจากหลักฐานของ", fallback)
        self.assertIn("Bubble Sort", fallback)
        self.assertIn("Selection Sort", fallback)
        self.assertIn("adjacent elements", fallback)
        self.assertIn("smallest remaining", fallback)
        self.assertIn("หลักฐานในเอกสารเป็นภาษาอังกฤษ", fallback)

    def test_empty_model_stream_returns_safe_notice_not_raw_evidence(self):
        service = object.__new__(RAGService)
        service.settings = Settings(gemini_api_key="test-key")
        service.client = SimpleNamespace(
            models=SimpleNamespace(
                generate_content_stream=lambda **kwargs: iter(()),
            )
        )
        hit = SearchHit(
            source_id="counting",
            source_file="counting sort.pdf",
            page_number=1,
            chunk_index=0,
            content="Counting Sort is an algorithm that sorts an array in O(n + k) time.",
            score=0.9,
            vector_score=0.9,
            lexical_score=0.9,
        )
        result = RetrievalResult(
            query="counting sort คืออะไร",
            retrieval_query="counting sort คืออะไร",
            hits=[hit],
            elapsed_ms=0.0,
        )

        answer = "".join(
            service.stream_answer(
                query=result.query,
                result=result,
                history=[],
                language_mode="thai",
            )
        )

        self.assertIn("สร้างคำตอบจากเอกสารไม่สำเร็จ", answer)
        self.assertNotIn("Counting Sort is an algorithm", answer)

    def test_model_timeout_returns_safe_notice_not_raw_evidence(self):
        def timeout(**kwargs):
            raise TimeoutError("generation deadline")

        service = object.__new__(RAGService)
        service.settings = Settings(gemini_api_key="test-key")
        service.client = SimpleNamespace(
            models=SimpleNamespace(generate_content_stream=timeout),
        )
        evidence = "Counting Sort is an algorithm that sorts an array in O(n + k) time."
        hit = SearchHit(
            source_id="counting",
            source_file="counting sort.pdf",
            page_number=1,
            chunk_index=0,
            content=evidence,
            score=0.9,
            vector_score=0.9,
            lexical_score=0.9,
        )
        result = RetrievalResult(
            query="counting sort คืออะไร",
            retrieval_query="counting sort คืออะไร",
            hits=[hit],
            elapsed_ms=0.0,
        )

        answer = "".join(
            service.stream_answer(
                query=result.query,
                result=result,
                history=[],
                language_mode="thai",
            )
        )

        self.assertIn("สร้างคำตอบจากเอกสารไม่สำเร็จ", answer)
        self.assertNotIn(evidence, answer)

    def test_coursewide_big_o_uses_grounded_table_without_generation(self):
        generation_calls = []

        def timeout(**kwargs):
            generation_calls.append(kwargs)
            raise TimeoutError("generation deadline")

        def empty_stream(**kwargs):
            generation_calls.append(kwargs)
            return iter(())

        def unreliable_response(**kwargs):
            generation_calls.append(kwargs)
            return iter((SimpleNamespace(text="Quick Sort has complexity O(n log n)."),))

        service = object.__new__(RAGService)
        service.settings = Settings(gemini_api_key="test-key")
        evidence_by_section = {
            "bubble_sort": "Bubble Sort worst case Θ(n^2); best case Θ(n).",
            "selection_sort": "Selection Sort number of comparisons Θ(n^2).",
            "insertion_sort": (
                "Insertion Sort best case Θ(n); worst case Θ(n^2); "
                "average case Θ(n^2)."
            ),
            "merge_sort": (
                "Merge sort: running time T(n) = Θ(n log n). "
                "Work per level is Θ(n)."
            ),
            "counting_sort": (
                "Counting Sort running time Θ(n + k); "
                "auxiliary storage is O(n)."
            ),
        }
        hits = [
            SearchHit(
                source_id=section,
                source_file=f"{section}.pdf",
                page_number=1,
                chunk_index=0,
                content=content,
                score=0.9,
                vector_score=0.9,
                lexical_score=0.9,
                metadata={"section": section, "curriculum_status": "primary"},
            )
            for section, content in evidence_by_section.items()
        ]
        query = "สรุป Big-O ของอัลกอริทึมการเรียงลำดับในบทเรียน"
        result = RetrievalResult(
            query=query,
            retrieval_query=service._retrieval_query(query, []),
            hits=hits,
            elapsed_ms=0.0,
        )

        for failure_mode, generator in (
            ("timeout", timeout),
            ("empty", empty_stream),
            ("unreliable_response", unreliable_response),
        ):
            for language_mode, expected_heading in (
                ("thai", "ความซับซ้อน"),
                ("english", "Time complexity"),
            ):
                with self.subTest(
                    failure_mode=failure_mode,
                    language_mode=language_mode,
                ):
                    generation_calls.clear()
                    service.client = SimpleNamespace(
                        models=SimpleNamespace(
                            generate_content_stream=generator,
                        ),
                    )
                    answer = "".join(
                        service.stream_answer(
                            query=query,
                            result=result,
                            history=[],
                            language_mode=language_mode,
                        )
                    )

                    self.assertIn(expected_heading, answer)
                    self.assertEqual(generation_calls, [])
                    self.assertIn("| Merge Sort | Θ(n log n) |", answer)
                    self.assertIn("| Counting Sort | Θ(n + k) |", answer)
                    self.assertNotIn("O(n)", answer)
                    for value in (
                        "Bubble Sort",
                        "Selection Sort",
                        "Insertion Sort",
                        "Merge Sort",
                        "Counting Sort",
                        "Θ(n²)",
                        "Θ(n log n)",
                        "Θ(n + k)",
                    ):
                        self.assertIn(value, answer)
                    for reference_only in ("Shell Sort", "Heap Sort", "Quick Sort"):
                        self.assertNotIn(reference_only, answer)
                    if language_mode == "thai":
                        self.assertIn("กรณีแย่ที่สุด: Θ(n²)", answer)
                        self.assertIn("กรณีดีที่สุด: Θ(n)", answer)
                        self.assertIn("จำนวนการเปรียบเทียบ: Θ(n²)", answer)
                        self.assertIn(
                            "| Insertion Sort | กรณีดีที่สุด: Θ(n); "
                            "กรณีแย่ที่สุด: Θ(n²); กรณีเฉลี่ย: Θ(n²) |",
                            answer,
                        )
                    else:
                        self.assertIn("Worst case: Θ(n²)", answer)
                        self.assertIn("Best case: Θ(n)", answer)
                        self.assertIn("Comparisons: Θ(n²)", answer)
                        self.assertIn(
                            "| Insertion Sort | Best case: Θ(n); "
                            "Worst case: Θ(n²); Average case: Θ(n²) |",
                            answer,
                        )


class ImagePreviewTests(unittest.TestCase):
    def test_preview_groups_preserve_order_and_pack_rows(self):
        images = [{"image_index": index} for index in range(1, 8)]

        groups = image_preview_groups(images, columns=3)

        self.assertEqual(
            [[item["image_index"] for item in group] for group in groups],
            [[1, 2, 3], [4, 5, 6], [7]],
        )

    def test_preview_caption_is_short_but_keeps_label_and_page(self):
        caption = compact_image_caption(
            {"label": "Selection Sort ขั้นตอนที่ 1"},
            page_number=8,
            index=1,
        )

        self.assertEqual(caption, "Selection Sort ขั้นตอนที่ 1 · หน้า 8")


if __name__ == "__main__":
    unittest.main()
