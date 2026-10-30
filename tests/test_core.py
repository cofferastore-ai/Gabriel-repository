import unittest
from datetime import datetime, timezone

from vvm import captions, research
from vvm.tts import Word


class Core(unittest.TestCase):
    def test_parse_duration(self):
        self.assertEqual(research.parse_duration("PT45S"), 45)
        self.assertEqual(research.parse_duration("PT1M5S"), 65)
        self.assertEqual(research.parse_duration("PT1H"), 3600)
        self.assertEqual(research.parse_duration("lixo"), 0)

    def test_score(self):
        now = datetime(2026, 10, 30, tzinfo=timezone.utc)
        v = research.score({"published": "2026-10-28T00:00:00Z", "views": 200_000, "subs": 10_000}, now)
        self.assertEqual(v["views_per_day"], 100_000)
        self.assertEqual(v["outlier"], 20.0)

    def test_analyze(self):
        vids = [{"title": "5 fatos sobre Roma?", "seconds": 40}, {"title": "A queda de Roma!", "seconds": 50}]
        a = research.analyze(vids)
        self.assertEqual(a["pct_titulo_com_numero"], 50)
        self.assertEqual(a["palavras_mais_comuns"][0][0], "roma")

    def test_estimate_words_cover_duration(self):
        w = captions.estimate_words("um dois três quatro", 4.0)
        self.assertAlmostEqual(w[-1].end, 4.0, places=3)
        self.assertTrue(all(a.end <= b.start + 1e-9 for a, b in zip(w, w[1:])))

    def test_ass_highlights_active_word(self):
        ass = captions.build_ass([(0.0, 2.0, [Word("oi", 0, 1), Word("mundo", 1, 2)])])
        self.assertIn(r"{\c&H00D7FF&}OI{\c&HFFFFFF&} MUNDO", ass)
        self.assertIn("0:00:01.00", ass)


if __name__ == "__main__":
    unittest.main()
