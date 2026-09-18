import unittest

from rag.query_lexicon import TOTAL_ALIASES, match_alias


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
            "ควิกซอท": "Quick Sort",
            "ฮีบซอท": "Heap Sort",
        }
        for query, expected in cases.items():
            match = match_alias(query, "topics")
            self.assertIsNotNone(match, query)
            self.assertEqual(match.canonical, expected)

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
