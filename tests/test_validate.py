import unittest

from addon_manifest import schema


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
