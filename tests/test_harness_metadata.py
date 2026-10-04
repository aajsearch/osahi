from osahi.capability import AllowlistPolicy
from osahi.clock import FrozenClock
from osahi.harness import ReferenceHarness
from osahi.ids import SequentialIds
from osahi.model import ScriptedModel
from osahi.schema import validate_document


def _harness(metadata=None):
    return ReferenceHarness(
        model=ScriptedModel([{"kind": "finish", "text": "done"}]),
        tools=[],
        policy=AllowlistPolicy(set()),
        clock=FrozenClock("2026-10-04T04:30:00Z"),
        ids=SequentialIds(),
        workload={"id": "wl_audit", "name": "audit"},
        model_ref={"provider": "scripted", "name": "fixture-model"},
        harness_ref={"name": "osahi-reference", "version": "0.1.0"},
        metadata=metadata,
    )


def test_run_started_records_audit_metadata_without_changing_the_event_type():
    harness = _harness({"owner": "platform-team", "environment": "production"})
    harness.run_until_blocked()
    started = harness.events()[0]
    assert started["type"] == "run.started"
    assert started["payload"]["metadata"] == {"owner": "platform-team", "environment": "production"}
    assert started["payload"]["workload"]["id"] == "wl_audit"
    assert started["payload"]["harness"]["name"] == "osahi-reference"
    assert harness.run["metadata"]["owner"] == "platform-team"
    validate_document(started, "trajectory-event.schema.json")


def test_omitted_metadata_is_an_empty_object_on_the_event():
    harness = _harness()
    harness.start()
    assert harness.events()[0]["payload"]["metadata"] == {}
