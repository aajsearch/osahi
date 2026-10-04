"""Load the published JSON Schemas and validate wire documents."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from osahi import SPEC_VERSION

_SCHEMA_BY_EXAMPLE = {
    "agent-run.json": "agent-run.schema.json",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def schema_dir() -> Path:
    return repo_root() / "schemas"


def load_schema(name: str) -> dict:
    return json.loads((schema_dir() / name).read_text(encoding="utf-8"))


def validate_document(instance: object, schema_name: str) -> None:
    jsonschema.validate(instance, load_schema(schema_name))


def example_paths() -> list[Path]:
    return sorted((schema_dir() / "examples").glob("*.json"))


def schema_for_example(path: Path) -> str:
    return _SCHEMA_BY_EXAMPLE.get(path.name, "trajectory-event.schema.json")


def assert_spec_version(value: str) -> None:
    if value != SPEC_VERSION:
        raise ValueError(f"unsupported spec_version {value}")
