import unittest

from rag.query_lexicon import (
    PRIMARY_CURRICULUM_TOPICS,
    PRIMARY_SORT_TOPICS,
    TOTAL_ALIASES,
    match_alias,
)


class QueryLexiconTests(unittest.TestCase):
    def test_alias_coverage_exceeds_requirement(self):
        self.assertGreaterEqual(TOTAL_ALIASES, 300)

    def test_social_variants(self):
        for query in ("ไง", "สวัสดีครับ", "ว่าไงง", "hello there"):
            match = match_alias(
                query,
                "social",
                allow_substring=False,
            )
            self.assertIsNotNone(match, query)
            self.assertEqual(match.canonical, "greeting")

    def test_algorithm_transliteration_and_typos(self):
        cases = {
            "บับเบิลซอร์ท": "Bubble Sort",
            "บับเบลซอรท": "Bubble Sort",
            "ซีเล็กชั่นซอร์ท": "Selection Sort",
            "อินเซิรชันซอท": "Insertion Sort",
            "เมิจซอท": "Merge Sort",
            "เคาน์ติ้งซอร์ท": "Counting Sort",
        }
        for query, expected in cases.items():
            match = match_alias(query, "topics")
            self.assertIsNotNone(match, query)
            self.assertEqual(match.canonical, expected)

    def test_primary_curriculum_matches_source_image_exactly(self):
        self.assertEqual(
            PRIMARY_CURRICULUM_TOPICS,
            (
                "หลักการเรียงลำดับข้อมูล",
                "Bubble Sort",
                "Selection Sort",
                "Insertion Sort",
                "Merge Sort",
                "Counting Sort",
            ),
        )
        self.assertEqual(
            PRIMARY_SORT_TOPICS,
            (
                "Bubble Sort",
                "Selection Sort",
                "Insertion Sort",
                "Merge Sort",
                "Counting Sort",
            ),
        )
        for excluded_topic in ("Shell Sort", "Quick Sort", "Heap Sort"):
            self.assertIsNone(match_alias(excluded_topic, "topics"))
            excluded = match_alias(
                excluded_topic,
                "non_curriculum_topics",
            )
            self.assertIsNotNone(excluded)
            self.assertEqual(excluded.canonical, excluded_topic)

    def test_concept_variants(self):
        cases = {
            "บิ๊กโอ": "time complexity Big-O",
            "ไทมคอมเพลกซิตี": "time complexity Big-O",
            "สเตเบิลล": "stable sorting stability",
            "ดิวายแอนคองเคอ": "divide and conquer",
        }
        for query, expected in cases.items():
            match = match_alias(query, "concepts")
            self.assertIsNotNone(match, query)
            self.assertEqual(match.canonical, expected)

    def test_unrelated_query_is_not_social_or_topic(self):
        query = "วันนี้อากาศเป็นยังไง"
        self.assertIsNone(
            match_alias(query, "social", allow_substring=False)
        )
        self.assertIsNone(match_alias(query, "topics"))


if __name__ == "__main__":
    unittest.main()
