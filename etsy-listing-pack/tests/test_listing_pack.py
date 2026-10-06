import json
import tempfile
import unittest
from pathlib import Path

from elp.load import enrich, load_json
from elp.render import build_pack
from elp.rules import TAG_COUNT, TAG_MAX, TITLE_MAX, validate_listing

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def _pack():
    progress = load_json(DATA / "publish-status.json")
    listings = enrich(
        load_json(DATA / "marketing-aop-listings.json"),
        load_json(DATA / "design-slugs.json"),
        progress,
    )
    return listings, progress


class RealCopyTests(unittest.TestCase):
    def test_sixteen_listings_pass_title_and_tag_rules(self):
        listings, _progress = _pack()
        self.assertEqual(len(listings), 16)
        slugs = {row["slug"] for row in listings}
        self.assertEqual(len(slugs), 8)
        self.assertEqual({row["fabric"] for row in listings}, {"poly", "cotton"})
        for listing in listings:
            self.assertLessEqual(len(listing["title"]), TITLE_MAX)
            self.assertEqual(len(listing["tags"]), TAG_COUNT)
            for tag in listing["tags"]:
                self.assertLessEqual(len(tag), TAG_MAX)
                self.assertGreater(len(tag), 0)
            self.assertEqual(validate_listing(listing), [])

    def test_only_last_ronin_poly_is_live(self):
        listings, _progress = _pack()
        live = [row for row in listings if row["publish_state"] == "live"]
        self.assertEqual(len(live), 1)
        self.assertEqual(live[0]["slug"], "crimson-sun-last-ronin")
        self.assertEqual(live[0]["fabric"], "poly")
        self.assertEqual(live[0]["etsy_url"], "https://www.etsy.com/listing/4589600597")
        self.assertEqual(live[0]["printful_template_id"], 108436673)
        unpublished = [row for row in listings if row["publish_state"] != "live"]
        self.assertEqual(len(unpublished), 15)

    def test_build_writes_paste_files(self):
        listings, progress = _pack()
        with tempfile.TemporaryDirectory() as tmp:
            errors, report = build_pack(listings, tmp, progress["note"])
            self.assertEqual(errors, [])
            out = Path(tmp)
            self.assertTrue(report.exists())
            files = list((out / "listings").glob("*.md"))
            self.assertEqual(len(files), 16)
            live = (out / "listings" / "crimson-sun-last-ronin-poly.md").read_text(encoding="utf-8")
            self.assertIn("Already live", live)
            self.assertIn("https://www.etsy.com/listing/4589600597", live)
            waiting = (out / "listings" / "ronin-last-stand-cotton.md").read_text(encoding="utf-8")
            self.assertIn("after Jason says go", waiting)
            saved = json.loads((out / "listings.json").read_text(encoding="utf-8"))
            self.assertEqual(len(saved), 16)


class RuleTests(unittest.TestCase):
    def _sample(self):
        listings, _progress = _pack()
        return dict(listings[0])

    def test_title_over_140_fails(self):
        listing = self._sample()
        listing["title"] = "Rogers Inc Designs " + ("x" * 140)
        errors = validate_listing(listing)
        self.assertTrue(any("title is" in error for error in errors))

    def test_title_at_140_can_pass_length_check(self):
        listing = self._sample()
        prefix = "Polyester Rogers Inc Designs "
        listing["title"] = prefix + ("a" * (TITLE_MAX - len(prefix)))
        errors = validate_listing(listing)
        self.assertFalse(any("title is" in error for error in errors))
        self.assertEqual(len(listing["title"]), TITLE_MAX)

    def test_wrong_tag_count_and_length_fail(self):
        listing = self._sample()
        listing["tags"] = ["ok"] * 12
        self.assertTrue(any("expected 13 tags" in error for error in validate_listing(listing)))
        listing["tags"] = ["ok"] * 12 + ["x" * (TAG_MAX + 1)]
        errors = validate_listing(listing)
        self.assertTrue(any("limit is 20" in error for error in errors))

    def test_builder_and_wrong_price_fail(self):
        listing = self._sample()
        listing["title"] = listing["title"].replace("Samurai", "builder")
        self.assertTrue(any("banned wording" in error for error in validate_listing(listing)))
        listing = self._sample()
        listing["price_aud"] = 1
        self.assertTrue(any("price_aud" in error for error in validate_listing(listing)))

    def test_duplicate_tag_fails(self):
        listing = self._sample()
        listing["tags"] = [listing["tags"][0]] + listing["tags"][:-1]
        self.assertTrue(any("duplicate tag" in error for error in validate_listing(listing)))


if __name__ == "__main__":
    unittest.main()
