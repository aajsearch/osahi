import json
from pathlib import Path

import jsonschema
import pytest

from osahi.config import load_config
from osahi.schema import example_paths, load_schema, repo_root, schema_for_example, validate_document


def test_harness_config_schema_id_is_not_a_wire_urn():
    schema = load_schema("harness-config.schema.json")
    assert schema["$id"] == "urn:osahi:reference:harness-config"
    assert schema["description"].startswith("This file configures the reference package only.")


def test_published_examples_match_their_schemas():
    paths = example_paths()
    assert paths, "schemas/examples must not be empty"
    for path in paths:
        validate_document(json.loads(path.read_text(encoding="utf-8")), schema_for_example(path))


def test_run_missing_identifier_is_rejected():
    document = json.loads(
        next(path for path in example_paths() if path.name == "agent-run.json").read_text()
    )
    del document["run_id"]
    with pytest.raises(jsonschema.ValidationError):
        validate_document(document, "agent-run.schema.json")


def test_checkpoint_without_scratchpad_is_rejected():
    document = json.loads(
        next(path for path in example_paths() if path.name == "checkpoint-created.json").read_text()
    )
    del document["payload"]["snapshot"]["scratchpad"]
    with pytest.raises(jsonschema.ValidationError):
        validate_document(document, "trajectory-event.schema.json")


_WIRE_SCHEMAS = {"agent-run.schema.json", "trajectory-event.schema.json"}


def test_wire_examples_do_not_include_reference_config():
    paths = example_paths()
    names = {path.name for path in paths}
    assert paths, "schemas/examples must not be empty"
    assert "harness-config-startup.json" not in names
    assert "harness-config-enterprise.json" not in names
    assert not any(name.startswith("harness-config") for name in names)
    for path in paths:
        assert schema_for_example(path) in _WIRE_SCHEMAS
    for name in ("harness-config-startup.json", "harness-config-enterprise.json"):
        assert schema_for_example(Path(name)) != "harness-config.schema.json"


def test_profile_json_is_validated_by_the_config_loader():
    example_names = {path.name for path in example_paths()}
    for name in ("startup", "enterprise"):
        path = repo_root() / "profiles" / f"{name}.json"
        assert path.is_file()
        assert path.name not in example_names
        config = load_config(path)
        assert config.profile == name


def test_capability_effect_outside_allow_or_deny_is_rejected():
    document = json.loads(
        next(path for path in example_paths() if path.name == "capability-decided.json").read_text()
    )
    document["payload"]["effect"] = "maybe"
    with pytest.raises(jsonschema.ValidationError):
        validate_document(document, "trajectory-event.schema.json")
