import json

import jsonschema
import pytest

from osahi.schema import example_paths, load_schema, schema_for_example, validate_document


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


def _startup_config() -> dict:
    path = next(path for path in example_paths() if path.name == "harness-config-startup.json")
    return json.loads(path.read_text(encoding="utf-8"))


def test_harness_config_examples_are_startup_and_enterprise():
    names = {path.name for path in example_paths()}
    assert "harness-config-startup.json" in names
    assert "harness-config-enterprise.json" in names


@pytest.mark.parametrize(
    "mutate",
    [
        "missing-allow",
        "budget-1",
        "unknown-profile",
        "missing-workload-id",
    ],
)
def test_harness_config_rejects_unsafe_documents(mutate):
    document = _startup_config()
    if mutate == "missing-allow":
        del document["policy"]["allow"]
    elif mutate == "budget-1":
        document["context"]["budget"] = 1
    elif mutate == "unknown-profile":
        document["profile"] = "platform"
    elif mutate == "missing-workload-id":
        del document["workload"]["id"]
    with pytest.raises(jsonschema.ValidationError):
        validate_document(document, "harness-config.schema.json")


def test_capability_effect_outside_allow_or_deny_is_rejected():
    document = json.loads(
        next(path for path in example_paths() if path.name == "capability-decided.json").read_text()
    )
    document["payload"]["effect"] = "maybe"
    with pytest.raises(jsonschema.ValidationError):
        validate_document(document, "trajectory-event.schema.json")
