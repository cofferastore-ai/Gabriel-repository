import unittest
from datetime import datetime, timezone

from vvm import animate, captions, images, research, script
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

    def test_caption_chunks_fit_screen(self):
        from vvm import visuals
        words = [Word(w, i, i + 1) for i, w in enumerate("ANOS QUASE QUINHENTOS reais, muito grande hoje".split())]
        f = visuals.font(captions.FONT_SIZE)
        chunks = captions.chunk_words(words)
        self.assertEqual([w for c in chunks for w in c], words)
        for c in chunks:
            self.assertLessEqual(len(c), 3)
            self.assertLess(f.getlength(" ".join(w.text.upper() for w in c)), 1000, c)

    def test_single_long_word_is_shrunk(self):
        ass = captions.build_ass([(0.0, 2.0, [Word("extraordinariamente", 0, 1), Word("ok", 1, 2)])])
        self.assertRegex(ass, r"Dialogue: 0,0:00:00\.00,[^,]+,Cap,,0,0,0,,\{\\fs\d+\}")
        self.assertNotRegex(ass.split("[Events]")[1].split("\n")[2], r"\\fs\d+\}.*ok")  # chunk só da palavra longa

    def test_language_filter(self):
        pt = research.is_portuguese
        self.assertTrue(pt("O Truque Matemático Que Mudou Tudo...🧠#curiosidades"))
        self.assertTrue(pt("Você sobreviveria ao primeiro minuto da bomba de Hiroshima?"))
        self.assertTrue(pt("qualquer coisa", "pt-BR"))
        self.assertFalse(pt("El Sonido que Todos TEMEN en la Guerra"))
        self.assertFalse(pt("Why There Are TWO Indias in the World"))
        self.assertFalse(pt("O Truque", "en"))
        self.assertFalse(pt("#shorts #viral"))

    def test_all_example_scripts_are_valid(self):
        import pathlib
        files = sorted(pathlib.Path("scripts/examples").glob("*.json"))
        self.assertGreaterEqual(len(files), 9)
        for f in files:
            sc = script.load(f)
            words = len(sc.narration.split())
            self.assertTrue(180 <= words <= 320, f"{f.name}: {words} palavras")
            self.assertTrue(any(s.kind for s in sc.scenes), f"{f.name}: sem cena animada")
            self.assertTrue(any(s.image_query for s in sc.scenes) or sc.niche != "historia", f.name)

    def test_fmt_ptbr(self):
        self.assertEqual(animate.fmt(115019, "R$ "), "R$ 115.019")
        self.assertEqual(animate.fmt(1234.5, decimals=1, suffix="%"), "1.234,5%")

    def test_growth_series_matches_formula(self):
        total, invested = animate.growth_series(500, 0.01, 120)
        self.assertAlmostEqual(total[-1], 500 * ((1.01 ** 120 - 1) / 0.01), places=4)
        self.assertEqual(invested[-1], 60000)

    def test_license_filter(self):
        rank = images._license_rank
        self.assertEqual(rank("Public domain"), 0)
        self.assertEqual(rank("CC0"), 0)
        self.assertEqual(rank("CC BY 4.0"), 1)
        for bad in ("CC BY-SA 4.0", "CC BY-NC 2.0", "CC BY-ND 2.0", "GFDL", "Fair use", ""):
            self.assertIsNone(rank(bad), bad)

    def test_pick_prefers_public_domain_and_skips_bad(self):
        def page(i, lic, w=2000, mime="image/jpeg"):
            return {"title": f"File:{i}.jpg", "index": i, "imageinfo": [{
                "thumburl": f"https://x/{i}.jpg", "mime": mime, "width": w,
                "extmetadata": {"LicenseShortName": {"value": lic}, "Artist": {"value": "<b>Ana</b>"}}}]}
        pages = {"1": page(1, "CC BY-SA 4.0"), "2": page(2, "CC BY 4.0"), "3": page(3, "Public domain"),
                 "4": page(4, "Public domain", w=300), "5": page(5, "Public domain", mime="image/svg+xml")}
        best = images.pick(pages)
        self.assertEqual(best["url"], "https://x/3.jpg")
        self.assertFalse(best["needs_credit"])
        self.assertIsNone(images.pick({"1": page(1, "CC BY-NC 2.0")}))

    def test_script_validation(self):
        import json, tempfile, pathlib
        d = pathlib.Path(tempfile.mkdtemp())
        f = d / "x.json"
        f.write_text(json.dumps({"title": "t", "scenes": [{"narration": "oi", "kind": "counter"}]}))
        with self.assertRaises(ValueError):  # counter sem data
            script.load(f)
        f.write_text(json.dumps({"title": "t", "scenes": [{"narration": "oi", "kind": "voando"}]}))
        with self.assertRaises(ValueError):  # kind inexistente
            script.load(f)


if __name__ == "__main__":
    unittest.main()
