import pytest

from osahi.errors import InvalidEvent
from osahi.log import EventLog


def _event(event_id: str = "evt_0001", **overrides) -> dict:
    event = {
        "event_id": event_id,
        "run_id": "run_0001",
        "type": "run.started",
        "at": "2026-10-04T04:30:00Z",
        "payload": {"spec_version": "0.1.0"},
        "causation_id": None,
        "correlation_id": "run_0001",
    }
    event.update(overrides)
    return event


def test_append_assigns_contiguous_sequence_and_hides_internal_list():
    log = EventLog()
    first = log.append(_event())
    second = log.append(_event("evt_0002", type="run.completed", payload={"text": "done"}))
    assert first["seq"] == 1
    assert second["seq"] == 2
    exported = log.events()
    exported[0]["type"] = "tampered"
    assert log.events()[0]["type"] == "run.started"


def test_caller_cannot_choose_sequence_or_reuse_an_identifier():
    log = EventLog()
    log.append(_event())
    with pytest.raises(InvalidEvent, match="seq is assigned"):
        log.append(_event("evt_0002", seq=2))
    with pytest.raises(InvalidEvent, match="duplicate"):
        log.append(_event("evt_0001", type="run.completed", payload={"text": ""}))


def test_log_rejects_a_second_run_and_a_mismatched_correlation_id():
    log = EventLog()
    log.append(_event())
    with pytest.raises(InvalidEvent, match="run_id"):
        log.append(_event("evt_0002", run_id="run_9999", correlation_id="run_9999"))
    with pytest.raises(InvalidEvent, match="correlation_id"):
        log.append(_event("evt_0003", correlation_id="other"))
