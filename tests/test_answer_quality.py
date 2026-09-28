import unittest

from prompt import build_tutor_prompt
from rag.config import Settings
from rag.models import RetrievalResult, SearchHit
from rag.service import RAGService


def make_hit(
    *,
    section: str,
    content: str,
    score: float = 0.8,
    page_number: int = 1,
    chunk_index: int = 0,
) -> SearchHit:
    return SearchHit(
        source_id=section,
        source_file=f"{section}.pdf",
        page_number=page_number,
        chunk_index=chunk_index,
        content=content,
        score=score,
        vector_score=score,
        lexical_score=score,
        metadata={"section": section},
    )


class AnswerQualityTests(unittest.TestCase):
    def setUp(self):
        self.service = object.__new__(RAGService)

    def test_comparison_query_preserves_every_named_topic(self):
        query = "Bubble Sort กับ Selection Sort ต่างกันอย่างไร"

        self.assertEqual(
            RAGService.topic_targets(query),
            ["Bubble Sort", "Selection Sort"],
        )
        retrieval_query = self.service._retrieval_query(query, [])
        self.assertIn("Bubble Sort", retrieval_query)
        self.assertIn("Selection Sort", retrieval_query)

    def test_coursewide_big_o_query_targets_only_primary_algorithms(self):
        query = "สรุป Big-O ของอัลกอริทึมการเรียงลำดับในบทเรียน"

        retrieval_query = self.service._retrieval_query(query, [])

        self.assertEqual(
            set(RAGService.topic_targets(retrieval_query)),
            {
                "Bubble Sort",
                "Selection Sort",
                "Insertion Sort",
                "Merge Sort",
                "Counting Sort",
            },
        )
        for out_of_scope in ("Shell Sort", "Heap Sort", "Quick Sort"):
            self.assertNotIn(out_of_scope, retrieval_query)

    def test_coursewide_big_o_retrieval_fans_out_with_complexity_focus(self):
        class FakeEmbedder:
            def embed_query(self, query):
                return [float(len(query))]

        class FakeStore:
            requires_query_embedding = False

            def __init__(self):
                self.queries = []

            def search(self, query, query_vector, *, top_k, candidate_k):
                self.queries.append(query)
                targets = RAGService.topic_targets(query)
                if len(targets) == 1:
                    topic = targets[0]
                    section = topic.casefold().replace(" ", "_")
                    notation = "O(n + k)" if topic == "Counting Sort" else "O(n^2)"
                    return [
                        make_hit(
                            section=section,
                            content=f"{topic} time complexity {notation}",
                        )
                    ]
                return [
                    make_hit(
                        section="fundamentals",
                        content="Sorting overview mentions Shell Sort and Heap Sort.",
                        score=0.99,
                    )
                ]

        service = object.__new__(RAGService)
        service.settings = Settings(
            gemini_api_key="test-key",
            top_k=5,
            candidate_k=18,
        )
        service.embedder = FakeEmbedder()
        service.store = FakeStore()

        result = service.retrieve(
            "สรุป Big-O ของอัลกอริทึมการเรียงลำดับในบทเรียน",
            [],
        )

        sections = {hit.metadata.get("section") for hit in result.hits}
        self.assertEqual(
            sections,
            {
                "bubble_sort",
                "selection_sort",
                "insertion_sort",
                "merge_sort",
                "counting_sort",
            },
        )
        focused_queries = [
            query
            for query in service.store.queries
            if len(RAGService.topic_targets(query)) == 1
        ]
        self.assertEqual(len(focused_queries), 5)
        self.assertTrue(
            all("time complexity" in query.casefold() for query in focused_queries)
        )

    def test_coursewide_big_o_requires_evidence_for_all_five_algorithms(self):
        self.service.settings = Settings(gemini_api_key="test-key")
        query = "สรุป Big-O ของอัลกอริทึมการเรียงลำดับในบทเรียน"
        retrieval_query = self.service._retrieval_query(query, [])
        partial = [
            make_hit(
                section="bubble_sort",
                content="Bubble Sort time complexity O(n^2)",
            ),
            make_hit(
                section="selection_sort",
                content="Selection Sort time complexity O(n^2)",
            ),
        ]
        complete = partial + [
            make_hit(
                section=section,
                content=f"{topic} time complexity {notation}",
                score=0.2,
            )
            for section, topic, notation in (
                ("insertion_sort", "Insertion Sort", "O(n^2)"),
                ("merge_sort", "Merge Sort", "O(n log n)"),
                ("counting_sort", "Counting Sort", "O(n + k)"),
            )
        ]

        partial_result = RetrievalResult(query, retrieval_query, partial, 0.0)
        complete_result = RetrievalResult(query, retrieval_query, complete, 0.0)

        self.assertFalse(self.service.answerable(partial_result))
        self.assertTrue(self.service.answerable(complete_result))

    def test_coursewide_summary_prefers_merge_sort_total_over_merge_operation(self):
        hits = [
            make_hit(
                section="bubble_sort",
                content="Bubble Sort worst case time complexity O(n^2)",
            ),
            make_hit(
                section="selection_sort",
                content="Selection Sort comparisons Θ(n^2)",
            ),
            make_hit(
                section="insertion_sort",
                content="Insertion Sort average case Θ(n^2)",
            ),
            make_hit(
                section="merge_sort",
                content=(
                    "Merge operation: merging n total elements takes Θ(n) time. "
                    "Standard merge sort uses linear extra memory."
                ),
                score=0.99,
            ),
            make_hit(
                section="merge_sort",
                content="Merge sort running time recurrence gives Θ(n log n).",
                score=0.5,
            ),
            make_hit(
                section="counting_sort",
                content="Counting Sort running time Θ(n + k)",
            ),
        ]

        selected = RAGService._coursewide_complexity_hits(hits)
        merge_evidence = next(
            hit for hit in selected
            if hit.metadata.get("section") == "merge_sort"
        )

        self.assertIn("Θ(n log n)", merge_evidence.content)

    def test_coursewide_retrieval_refetches_merge_sort_total_after_merge_step(self):
        class FakeEmbedder:
            def embed_query(self, query):
                return [float(len(query))]

        merge_step = make_hit(
            section="merge_sort",
            content=(
                "Merge operation: merging n total elements takes Θ(n) time. "
                "Merge sort uses linear extra memory."
            ),
            score=0.99,
        )
        primary_hits = [
            make_hit(
                section="bubble_sort",
                content="Bubble Sort worst case time complexity Θ(n^2)",
            ),
            make_hit(
                section="selection_sort",
                content="Selection Sort number of comparisons Θ(n^2)",
            ),
            make_hit(
                section="insertion_sort",
                content="Insertion Sort time complexity Θ(n^2)",
            ),
            merge_step,
            make_hit(
                section="counting_sort",
                content="Counting Sort running time Θ(n + k)",
            ),
        ]
        merge_total = make_hit(
            section="merge_sort",
            content="Merge sort running time T(n) = Θ(n log n).",
            score=0.4,
            page_number=31,
        )

        class FakeStore:
            requires_query_embedding = False

            def __init__(self):
                self.queries = []

            def search(self, query, query_vector, *, top_k, candidate_k):
                self.queries.append(query)
                if RAGService.topic_targets(query) == ["Merge Sort"]:
                    return [merge_total]
                return primary_hits

        service = object.__new__(RAGService)
        service.settings = Settings(
            gemini_api_key="test-key",
            top_k=5,
            candidate_k=18,
        )
        service.embedder = FakeEmbedder()
        service.store = FakeStore()
        query = "สรุป Big-O ของอัลกอริทึมการเรียงลำดับในบทเรียน"

        result = service.retrieve(query, [])

        self.assertTrue(
            any(
                RAGService.topic_targets(search_query) == ["Merge Sort"]
                for search_query in service.store.queries
            )
        )
        self.assertTrue(service.answerable(result))
        merge_evidence = next(
            hit for hit in result.hits
            if hit.metadata.get("section") == "merge_sort"
        )
        self.assertIn("Θ(n log n)", merge_evidence.content)

    def test_comparison_rerank_keeps_both_target_sections_near_the_top(self):
        query = "Bubble Sort กับ Selection Sort ต่างกันอย่างไร"
        hits = [
            make_hit(
                section="selection_sort",
                content="Selection Sort เลือกค่าน้อยสุดแล้วสลับตำแหน่ง",
                score=0.95,
            ),
            make_hit(
                section="bubble_sort",
                content="Bubble Sort เปรียบเทียบสมาชิกที่อยู่ติดกัน",
                score=0.70,
            ),
            make_hit(
                section="insertion_sort",
                content="Insertion Sort แทรกสมาชิกลงในส่วนที่เรียงแล้ว",
                score=0.99,
            ),
        ]

        ranked = RAGService._rerank_topic_hits(query, hits)
        top_sections = {
            hit.metadata.get("section") for hit in ranked[:2]
        }
        self.assertEqual(top_sections, {"bubble_sort", "selection_sort"})

    def test_comparison_retrieval_fans_out_to_each_named_topic(self):
        class FakeEmbedder:
            def embed_query(self, query):
                return [float(len(query))]

        class FakeStore:
            requires_query_embedding = True

            def __init__(self):
                self.queries = []

            def search(self, query, query_vector, *, top_k, candidate_k):
                self.queries.append(query)
                if "Bubble Sort" in query and "Selection Sort" not in query:
                    return [
                        make_hit(
                            section="bubble_sort",
                            content="Bubble Sort เปรียบเทียบสมาชิกที่อยู่ติดกัน",
                            score=0.72,
                        )
                    ]
                return [
                    make_hit(
                        section="selection_sort",
                        content="Selection Sort เลือกค่าน้อยสุดแล้วสลับตำแหน่ง",
                        score=0.80,
                    )
                ]

        service = object.__new__(RAGService)
        service.settings = Settings(
            gemini_api_key="test-key",
            top_k=5,
            candidate_k=18,
        )
        service.embedder = FakeEmbedder()
        service.store = FakeStore()

        result = service.retrieve(
            "Bubble Sort กับ Selection Sort ต่างกันอย่างไร",
            [],
        )

        sections = {hit.metadata.get("section") for hit in result.hits}
        self.assertIn("bubble_sort", sections)
        self.assertIn("selection_sort", sections)
        self.assertEqual(result.hits[0].metadata.get("section"), "bubble_sort")
        self.assertEqual(len(service.store.queries), 2)
        self.assertTrue(
            any(
                "Bubble Sort" in query and "Selection Sort" not in query
                for query in service.store.queries
            )
        )

    def test_comparison_fallback_uses_evidence_for_both_topics(self):
        hits = [
            make_hit(
                section="selection_sort",
                content="Selection Sort เลือกค่าน้อยสุดแล้วสลับไปตำแหน่งที่ถูกต้อง",
                score=0.95,
            ),
            make_hit(
                section="bubble_sort",
                content="Bubble Sort เปรียบเทียบสมาชิกที่อยู่ติดกันและสลับเมื่อเรียงผิด",
                score=0.70,
            ),
        ]

        answer = self.service._fast_grounded_fallback(
            "Bubble Sort กับ Selection Sort ต่างกันอย่างไร",
            hits,
            "thai",
        )

        self.assertIn("Bubble Sort", answer)
        self.assertIn("Selection Sort", answer)
        self.assertIn("เปรียบเทียบสมาชิกที่อยู่ติดกัน", answer)
        self.assertIn("เลือกค่าน้อยสุด", answer)

    def test_visual_followup_does_not_collapse_comparison_to_one_topic(self):
        comparison = "Bubble Sort กับ Selection Sort ต่างกันอย่างไร"

        self.assertIsNone(self.service.visual_topic("ภาพ " + comparison, []))
        self.assertIsNone(
            self.service.visual_topic(
                "มีรูปประกอบไหม",
                [{"role": "user", "content": comparison}],
            )
        )

    def test_comparison_visual_followup_retrieves_previous_topics(self):
        class FakeEmbedder:
            def embed_query(self, query):
                return [float(len(query))]

        class FakeStore:
            requires_query_embedding = True

            def __init__(self):
                self.queries = []

            def search(self, query, query_vector, *, top_k, candidate_k):
                self.queries.append(query)
                if "Bubble Sort" in query and "Selection Sort" not in query:
                    return [
                        make_hit(
                            section="bubble_sort",
                            content="Bubble Sort เปรียบเทียบสมาชิกที่อยู่ติดกัน",
                            score=0.72,
                        )
                    ]
                return [
                    make_hit(
                        section="selection_sort",
                        content="Selection Sort เลือกค่าน้อยสุดแล้วสลับตำแหน่ง",
                        score=0.80,
                    )
                ]

        service = object.__new__(RAGService)
        service.settings = Settings(
            gemini_api_key="test-key",
            top_k=5,
            candidate_k=18,
        )
        service.embedder = FakeEmbedder()
        service.store = FakeStore()
        history = [
            {
                "role": "user",
                "content": "Bubble Sort กับ Selection Sort ต่างกันอย่างไร",
            }
        ]

        result = service.retrieve("มีรูปประกอบไหม", history)

        sections = {hit.metadata.get("section") for hit in result.hits}
        self.assertIn("bubble_sort", sections)
        self.assertIn("selection_sort", sections)
        self.assertEqual(result.hits[0].metadata.get("section"), "bubble_sort")

    def test_comparison_prompt_requires_all_named_topics(self):
        thai_prompt = build_tutor_prompt(
            "thai",
            "Bubble Sort กับ Selection Sort ต่างกันอย่างไร",
        )
        english_prompt = build_tutor_prompt(
            "english",
            "How are Bubble Sort and Selection Sort different?",
        )

        self.assertIn("ตอบครบทุกหัวข้อ", thai_prompt)
        self.assertIn("compare every named topic", english_prompt)

    def test_corrupted_pdf_hit_is_excluded_from_context(self):
        corrupted = make_hit(
            section="selection_sort",
            content=(
                "Selection Sort เป็นอัลกอริทึมแบบ in-place "
                "พืLนที4เพิ4มเติม O(1) เมื@อใดจึงเหมาะสม"
            ),
        )
        clean = make_hit(
            section="bubble_sort",
            content="Bubble Sort เปรียบเทียบสมาชิกที่อยู่ติดกันซ้ำ ๆ",
        )

        context = self.service._context_text([corrupted, clean])

        self.assertNotIn("พืLนที4เพิ4มเติม", context)
        self.assertNotIn("เมื@อใด", context)
        self.assertIn("Bubble Sort เปรียบเทียบสมาชิกที่อยู่ติดกันซ้ำ ๆ", context)

    def test_private_use_thai_pdf_glyphs_are_excluded_from_context(self):
        corrupted = make_hit(
            section="fundamentals",
            content="การเรียงลําดับขอมูล •เ ล ือก : Selection sort O(n 2)",
        )

        self.assertEqual(self.service._context_text([corrupted]), "")


if __name__ == "__main__":
    unittest.main()
