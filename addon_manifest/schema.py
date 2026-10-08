import json
import re
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema" / "manifest.schema.json"

ANNOTATIONS = {"$schema", "$id", "title"}
ASSERTIONS = {
    "$ref", "$defs", "type", "const", "enum", "minLength", "pattern", "minimum", "maximum",
    "minItems", "items", "required", "properties", "additionalProperties", "oneOf",
}
PYTHON_TYPES = {"object": dict, "array": list, "string": str}
TYPE_NAMES = (*PYTHON_TYPES, "integer", "boolean")


class UnsupportedKeyword(ValueError):
    pass


def load(path=SCHEMA_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _is(value, name):
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "boolean":
        return isinstance(value, bool)
    return isinstance(value, PYTHON_TYPES[name])


def _same(left, right):
    return type(left) is type(right) and left == right


def _refuse_unsupported(schema, path):
    unknown = set(schema) - ASSERTIONS - ANNOTATIONS
    if unknown:
        raise UnsupportedKeyword(f"{path}: {', '.join(sorted(unknown))}")
    if "type" in schema and schema["type"] not in TYPE_NAMES:
        raise UnsupportedKeyword(f"{path}: type {json.dumps(schema['type'])}")
    children = [(f"{path}/items", schema["items"])] if "items" in schema else []
    for group in ("properties", "$defs"):
        children += [(f"{path}/{group}/{name}", child) for name, child in schema.get(group, {}).items()]
    children += [(f"{path}/oneOf/{n}", child) for n, child in enumerate(schema.get("oneOf", []))]
    for child_path, child in children:
        _refuse_unsupported(child, child_path)


class Checker:
    def __init__(self, root):
        _refuse_unsupported(root, "#")
        self.root = root

    def errors(self, value):
        return list(self._check(value, self.root, "$"))

    def _resolve(self, reference):
        if not reference.startswith("#/"):
            raise UnsupportedKeyword(f"only local references are followed, not {reference}")
        target = self.root
        for part in reference[2:].split("/"):
            target = target[part]
        return target

    def _check(self, value, schema, path):
        if "$ref" in schema:
            yield from self._check(value, self._resolve(schema["$ref"]), path)
        if "type" in schema and not _is(value, schema["type"]):
            yield f"{path}: expected {schema['type']}"
            return
        if "const" in schema and not _same(value, schema["const"]):
            yield f"{path}: must be {json.dumps(schema['const'])}"
        if "enum" in schema and not any(_same(value, allowed) for allowed in schema["enum"]):
            yield f"{path}: {json.dumps(value)} is not one of {json.dumps(schema['enum'])}"
        if isinstance(value, str):
            if len(value) < schema.get("minLength", 0):
                yield f"{path}: shorter than {schema['minLength']}"
            if "pattern" in schema and not re.search(schema["pattern"], value):
                yield f"{path}: does not match {schema['pattern']}"
        if _is(value, "integer"):
            if "minimum" in schema and value < schema["minimum"]:
                yield f"{path}: below {schema['minimum']}"
            if "maximum" in schema and value > schema["maximum"]:
                yield f"{path}: above {schema['maximum']}"
        if isinstance(value, list):
            if len(value) < schema.get("minItems", 0):
                yield f"{path}: fewer than {schema['minItems']} items"
            if "items" in schema:
                for index, item in enumerate(value):
                    yield from self._check(item, schema["items"], f"{path}[{index}]")
        if isinstance(value, dict):
            for key in schema.get("required", ()):
                if key not in value:
                    yield f"{path}: missing {key}"
            properties = schema.get("properties", {})
            for key, item in value.items():
                if key in properties:
                    yield from self._check(item, properties[key], f"{path}.{key}")
                elif schema.get("additionalProperties", True) is False:
                    yield f"{path}: unknown key {key}"
        if "oneOf" in schema:
            matching = sum(not list(self._check(value, branch, path)) for branch in schema["oneOf"])
            if matching != 1:
                yield f"{path}: matches {matching} of the allowed shapes, not exactly one"
