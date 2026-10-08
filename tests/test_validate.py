import json
import unittest
from pathlib import Path

from addon_manifest import schema

REPOSITORY = Path(__file__).resolve().parent.parent
SITE = REPOSITORY / "site"
TRENDING = SITE / "trending" / "manifest.json"


def trending():
    return json.loads(TRENDING.read_text(encoding="utf-8"))


class PublishedSite(unittest.TestCase):
    def test_trending_is_first_party_and_declares_no_content(self):
        manifest = trending()
        self.assertEqual("sh.thirdshift.specula.trending", manifest["id"])
        self.assertEqual([], manifest["resources"])
        self.assertEqual([], manifest["catalogs"])


class SchemaChecker(unittest.TestCase):
    def test_a_keyword_the_checker_does_not_implement_is_refused(self):
        with self.assertRaises(schema.UnsupportedKeyword):
            schema.Checker({"type": "string", "format": "uri"})

    def test_a_keyword_deep_in_a_definition_is_refused(self):
        nested = {"$defs": {"row": {"oneOf": [{"properties": {"id": {"format": "uri"}}}]}}}
        with self.assertRaises(schema.UnsupportedKeyword):
            schema.Checker(nested)

    def test_a_type_the_checker_does_not_implement_is_refused(self):
        for name in ("number", "null"):
            with self.subTest(type=name), self.assertRaises(schema.UnsupportedKeyword):
                schema.Checker({"properties": {"count": {"type": name}}})


if __name__ == "__main__":
    unittest.main()
