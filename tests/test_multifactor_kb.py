import unittest

from multifactor_kb import build_ask_prompt, load_chunks, search


class MultifactorKbTests(unittest.TestCase):
    def test_chunks_loaded(self):
        chunks = load_chunks()
        self.assertGreater(len(chunks), 100)

    def test_search_value_momentum(self):
        hits = search("价值与动量负相关", top_k=5)
        self.assertTrue(hits)
        blob = " ".join(c.source + c.text for _, c in hits).lower()
        self.assertTrue(
            any(k in blob for k in ("momentum", "value", "动量", "价值", "asness")),
            msg="expected value/momentum related hit",
        )

    def test_search_five_factor_rmw(self):
        hits = search("五因子 RMW CMA HML 冗余", top_k=5)
        self.assertTrue(hits)
        sources = " ".join(c.source for _, c in hits).lower()
        self.assertTrue(
            "fama_french_2015" in sources or "digest/fama_french_2015" in sources
            or "five" in sources
            or "digest" in sources
        )

    def test_ask_prompt_contains_question(self):
        prompt = build_ask_prompt("什么是BAB", top_k=3)
        self.assertIn("BAB", prompt)
        self.assertIn("【资料】", prompt)
        self.assertIn("【问题】", prompt)
        self.assertIn("frazzini", prompt.lower())

    def test_mixed_chinese_english_query(self):
        hits = search("什么是BAB", top_k=3)
        self.assertTrue(hits)
        sources = " ".join(c.source for _, c in hits).lower()
        self.assertTrue(
            "frazzini" in sources or "bab" in sources,
            msg=f"unexpected sources: {sources}",
        )


if __name__ == "__main__":
    unittest.main()
