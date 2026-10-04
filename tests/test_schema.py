import json

import jsonschema
import pytest

from osahi.schema import example_paths, schema_for_example, validate_document


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


def test_capability_effect_outside_allow_or_deny_is_rejected():
    document = json.loads(
        next(path for path in example_paths() if path.name == "capability-decided.json").read_text()
    )
    document["payload"]["effect"] = "maybe"
    with pytest.raises(jsonschema.ValidationError):
        validate_document(document, "trajectory-event.schema.json")
