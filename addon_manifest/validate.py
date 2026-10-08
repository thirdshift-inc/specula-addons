import json
import re
import sys
from pathlib import Path

from . import schema

FIRST_PARTY_PREFIX = "sh.thirdshift."
ADDON_ID = re.compile(r"[a-z0-9]+(\.[a-z0-9][a-z0-9-]*)+")
MANIFEST_NAME = "manifest.json"
CONTENT_RESOURCES = {"stream", "catalog"}
QUERY_VOCABULARY = {
    "kind": {"trending", "popular"},
    "media": {"movie", "series", "all"},
    "window": {"day", "week"},
}


class DuplicateKey(ValueError):
    pass


def _repeated(values):
    return sorted({value for value in values if values.count(value) > 1})


def _unique_object(pairs):
    repeated = _repeated([key for key, _ in pairs])
    if repeated:
        raise DuplicateKey(", ".join(repeated))
    return dict(pairs)


def parse(text):
    return json.loads(text, object_pairs_hook=_unique_object)


def _kind_name(field):
    kind = field.get("kind")
    return next(iter(kind)) if isinstance(kind, dict) and len(kind) == 1 else None


def _identity_problems(manifest):
    addon_id = manifest["id"]
    problems = []
    if not addon_id.startswith(FIRST_PARTY_PREFIX):
        problems.append(f"id {addon_id!r} is not under {FIRST_PARTY_PREFIX}")
    if not ADDON_ID.fullmatch(addon_id):
        problems.append(f"id {addon_id!r} is not a lowercase reverse-domain name")
    return problems


def _content_problems(manifest):
    problems = []
    for resource in manifest.get("resources", []):
        name = resource if isinstance(resource, str) else resource.get("name")
        if name in CONTENT_RESOURCES:
            problems.append(f"declares the {name} resource")
    if manifest.get("catalogs"):
        problems.append("declares catalogues")
    return problems


def _option_problems(fields):
    problems = []
    for key in _repeated([field["key"] for field in fields]):
        problems.append(f"option {key!r} is declared more than once")
    for field in fields:
        kind = _kind_name(field)
        default = field.get("defaultValue")
        if kind == "secret" and default is not None:
            problems.append(f"option {field['key']!r} is a secret with a default")
        if kind == "choice":
            values = [choice["value"] for choice in field["kind"]["choice"]["options"]]
            for value in _repeated(values):
                problems.append(f"option {field['key']!r} lists {value!r} more than once")
            if default is not None and default not in values:
                problems.append(f"option {field['key']!r} defaults to {default!r}, which it does not list")
    return problems


def _row_problems(rows, fields):
    problems = []
    by_key = {field["key"]: field for field in fields}
    row_ids = [row["id"] for row in rows]
    for row_id in _repeated(row_ids):
        problems.append(f"row {row_id!r} is declared more than once")
    for row in rows:
        query = row.get("query")
        catalogue = row.get("catalogID")
        if query is None and catalogue is None:
            problems.append(f"row {row['id']!r} has neither a query nor a catalogue")
        if catalogue is not None:
            problems.append(f"row {row['id']!r} names catalogue {catalogue!r}")
        for slot, key in (query or {}).get("options", {}).items():
            field = by_key.get(key)
            if field is None:
                problems.append(f"row {row['id']!r} maps {slot} to option {key!r}, which is not declared")
                continue
            kind = _kind_name(field)
            if slot == "providers" and kind != "metadataProviders":
                problems.append(f"row {row['id']!r} maps providers to {key!r}, which is not a metadataProviders option")
            if slot in QUERY_VOCABULARY and kind == "choice":
                words = QUERY_VOCABULARY[slot]
                for choice in field["kind"]["choice"]["options"]:
                    if choice["value"] not in words:
                        problems.append(f"option {key!r} offers {choice['value']!r}, which is not a {slot} word")
    for field in fields:
        if _kind_name(field) == "metadataProviders":
            row_id = field["kind"]["metadataProviders"]["row"]
            if row_id not in row_ids:
                problems.append(f"option {field['key']!r} fills row {row_id!r}, which is not declared")
    return problems


def manifest_problems(manifest, checker=None):
    checker = checker or schema.Checker(schema.load())
    problems = checker.errors(manifest)
    if problems:
        return problems
    specula = manifest.get("specula", {})
    fields = specula.get("options", {}).get("fields", [])
    rows = specula.get("homeRows", [])
    return (_identity_problems(manifest) + _content_problems(manifest) + _option_problems(fields)
            + _row_problems(rows, fields))


def site_problems(site):
    site = Path(site)
    checker = schema.Checker(schema.load())
    problems = []
    manifests = sorted(site.glob(f"*/{MANIFEST_NAME}"))
    if not manifests:
        problems.append(f"{site}: no add-on manifests")
    for path in manifests:
        try:
            manifest = parse(path.read_text(encoding="utf-8"))
        except ValueError as error:
            problems.append(f"{path}: not a manifest: {error}")
            continue
        problems += [f"{path}: {problem}" for problem in manifest_problems(manifest, checker)]
    return problems


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    site = Path(arguments[0]) if arguments else Path("site")
    problems = site_problems(site)
    for problem in problems:
        print(problem, file=sys.stderr)
    if not problems:
        print(f"{site}: every manifest is valid")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
