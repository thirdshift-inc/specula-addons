import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path

from addon_manifest import schema, validate

REPOSITORY = Path(__file__).resolve().parent.parent
SITE = REPOSITORY / "site"
TRENDING = SITE / "trending" / "manifest.json"


def trending():
    return json.loads(TRENDING.read_text(encoding="utf-8"))


def field(manifest, key):
    return next(f for f in manifest["specula"]["options"]["fields"] if f["key"] == key)


def row(manifest, row_id="trending"):
    return next(r for r in manifest["specula"]["homeRows"] if r["id"] == row_id)


class PublishedSite(unittest.TestCase):
    def test_every_published_manifest_is_valid(self):
        self.assertEqual([], validate.site_problems(SITE))

    def test_trending_is_first_party_and_declares_no_content(self):
        manifest = trending()
        self.assertEqual("sh.thirdshift.specula.trending", manifest["id"])
        self.assertEqual([], manifest["resources"])
        self.assertEqual([], manifest["catalogs"])

    def test_the_command_passes_the_site(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, validate.main([str(SITE)]))


class GoodManifests(unittest.TestCase):
    def assertValid(self, manifest):
        self.assertEqual([], validate.manifest_problems(manifest))

    def test_a_row_with_only_a_kind_is_valid(self):
        manifest = trending()
        manifest["specula"]["homeRows"] = [{"id": "popular", "title": "Popular",
                                            "query": {"kind": "popular"}}]
        manifest["specula"]["options"]["fields"] = []
        self.assertValid(manifest)

    def test_a_metadata_or_subtitles_resource_is_not_content(self):
        for name in ("meta", "subtitles"):
            detailed = {"name": name, "types": ["movie", "series"], "idPrefixes": ["tt"]}
            for resource in (name, detailed):
                with self.subTest(resource=resource):
                    manifest = trending()
                    manifest["resources"] = [resource]
                    self.assertValid(manifest)

    def test_a_plain_text_option_is_valid(self):
        manifest = trending()
        manifest["specula"]["options"]["fields"].append(
            {"key": "region", "title": "Region", "kind": {"text": {"placeholder": "PL"}},
             "defaultValue": "PL"})
        self.assertValid(manifest)


class PlantedManifests(unittest.TestCase):
    def assertRefused(self, manifest, expected):
        problems = validate.manifest_problems(manifest)
        self.assertTrue(any(expected in problem for problem in problems),
                        f"{expected!r} not in {problems}")

    def planted(self, change):
        manifest = trending()
        change(manifest)
        return manifest

    def test_a_stream_resource_is_refused(self):
        self.assertRefused(self.planted(lambda m: m.update(resources=["stream"])),
                           "declares the stream resource")

    def test_a_detailed_stream_resource_is_refused(self):
        manifest = self.planted(lambda m: m.update(resources=[{"name": "stream", "types": ["movie"]}]))
        self.assertRefused(manifest, "declares the stream resource")

    def test_a_catalog_resource_is_refused(self):
        self.assertRefused(self.planted(lambda m: m.update(resources=["catalog"])),
                           "declares the catalog resource")

    def test_catalogue_content_is_refused(self):
        manifest = self.planted(lambda m: m.update(catalogs=[{"type": "movie", "id": "top"}]))
        self.assertRefused(manifest, "declares catalogues")

    def test_an_unknown_specula_key_is_refused(self):
        manifest = self.planted(lambda m: m["specula"].update(widgets=[]))
        self.assertRefused(manifest, "$.specula: unknown key widgets")

    def test_an_unknown_query_key_is_refused(self):
        manifest = self.planted(lambda m: row(m)["query"].update(region="PL"))
        self.assertRefused(manifest, "unknown key region")

    def test_an_unknown_top_level_key_is_refused(self):
        self.assertRefused(self.planted(lambda m: m.update(addonCatalogs=[])),
                           "$: unknown key addonCatalogs")

    def test_a_torrent_hint_is_refused(self):
        self.assertRefused(self.planted(lambda m: m.update(behaviorHints={"p2p": True})),
                           "$.behaviorHints.p2p: must be false")

    def test_a_secret_is_refused_only_with_a_default(self):
        def secret(**extra):
            return self.planted(lambda m: m["specula"]["options"]["fields"].append(
                {"key": "pin", "title": "PIN", "kind": {"secret": {}}, **extra}))
        self.assertEqual([], validate.manifest_problems(secret()))
        self.assertRefused(secret(defaultValue="1234"), "is a secret with a default")

    def test_a_query_option_naming_no_option_is_refused(self):
        manifest = self.planted(lambda m: row(m)["query"]["options"].update(window="period"))
        self.assertRefused(manifest, "maps window to option 'period', which is not declared")

    def test_providers_naming_a_choice_is_refused(self):
        manifest = self.planted(lambda m: row(m)["query"]["options"].update(providers="media"))
        self.assertRefused(manifest, "maps providers to 'media', which is not a metadataProviders option")

    def test_a_metadata_providers_row_naming_no_row_is_refused(self):
        def plant(manifest):
            field(manifest, "providers")["kind"]["metadataProviders"]["row"] = "popular"
        self.assertRefused(self.planted(plant), "fills row 'popular', which is not declared")

    def test_a_choice_default_that_is_not_listed_is_refused(self):
        manifest = self.planted(lambda m: field(m, "window").update(defaultValue="month"))
        self.assertRefused(manifest, "defaults to 'month', which it does not list")

    def test_a_mapped_choice_offering_a_word_outside_the_vocabulary_is_refused(self):
        def plant(manifest):
            field(manifest, "media")["kind"]["choice"]["options"].append(
                {"value": "films", "label": "Films only"})
        self.assertRefused(self.planted(plant), "offers 'films', which is not a media word")

    def test_an_unknown_query_kind_is_refused(self):
        manifest = self.planted(lambda m: row(m)["query"].update(kind="upcoming"))
        self.assertRefused(manifest, '"upcoming" is not one of')

    def test_a_count_outside_one_to_twenty_is_refused(self):
        for count, expected in ((0, "below 1"), (21, "above 20"), (True, "expected integer")):
            with self.subTest(count=count):
                manifest = self.planted(lambda m: row(m)["query"].update(count=count))
                self.assertRefused(manifest, expected)

    def test_an_id_outside_the_first_party_namespace_is_refused(self):
        manifest = self.planted(lambda m: m.update(id="dev.specula.trending"))
        self.assertRefused(manifest, "is not under sh.thirdshift.")

    def test_an_id_that_is_not_a_reverse_domain_name_is_refused(self):
        manifest = self.planted(lambda m: m.update(id="sh.thirdshift.Specula Trending"))
        self.assertRefused(manifest, "is not a lowercase reverse-domain name")

    def test_a_row_with_neither_query_nor_catalogue_is_refused(self):
        manifest = self.planted(lambda m: row(m).pop("query"))
        self.assertRefused(manifest, "has neither a query nor a catalogue")

    def test_a_row_naming_an_undeclared_catalogue_is_refused(self):
        manifest = self.planted(lambda m: row(m).update(catalogID="top"))
        self.assertRefused(manifest, "names catalogue 'top'")

    def test_a_repeated_row_is_refused(self):
        manifest = self.planted(lambda m: m["specula"]["homeRows"].append(copy.deepcopy(row(m))))
        self.assertRefused(manifest, "row 'trending' is declared more than once")

    def test_a_repeated_option_is_refused(self):
        def plant(manifest):
            manifest["specula"]["options"]["fields"].append(copy.deepcopy(field(manifest, "media")))
        self.assertRefused(self.planted(plant), "option 'media' is declared more than once")

    def test_an_option_kind_outside_the_vocabulary_is_refused(self):
        manifest = self.planted(lambda m: field(m, "media").update(kind={"slider": {}}))
        self.assertRefused(manifest, "matches 0 of the allowed shapes")


class PlantedSites(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.site = Path(self.scratch.name)
        (self.site / "trending").mkdir()
        (self.site / "trending" / "manifest.json").write_bytes(TRENDING.read_bytes())

    def tearDown(self):
        self.scratch.cleanup()

    def test_the_copy_is_valid(self):
        self.assertEqual([], validate.site_problems(self.site))

    def test_a_repeated_json_key_is_refused(self):
        text = TRENDING.read_text(encoding="utf-8").replace(
            '"name": "Trending",', '"name": "Trending", "name": "Streams",', 1)
        (self.site / "trending" / "manifest.json").write_text(text, encoding="utf-8")
        problems = validate.site_problems(self.site)
        self.assertEqual(1, len(problems))
        self.assertIn("not a manifest: name", problems[0])

    def test_a_bad_manifest_fails_the_command(self):
        manifest = trending()
        manifest["resources"] = ["stream"]
        (self.site / "trending" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        with contextlib.redirect_stderr(io.StringIO()) as report:
            self.assertEqual(1, validate.main([str(self.site)]))
        self.assertIn("declares the stream resource", report.getvalue())


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
