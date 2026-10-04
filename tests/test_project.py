from osahi.project import project


def _event(seq: int, event_type: str, payload: dict | None = None) -> dict:
    return {
        "event_id": f"evt_{seq:04d}",
        "run_id": "run_0001",
        "seq": seq,
        "type": event_type,
        "at": "2026-10-04T04:30:00Z",
        "payload": payload or {},
        "causation_id": None,
        "correlation_id": "run_0001",
    }


def test_fold_is_pure_and_merges_memory_without_decreasing_version():
    events = [
        _event(1, "run.started"),
        _event(2, "state.updated", {"patch": {"note": "a"}, "scratchpad": [{"role": "user", "content": "a"}]}),
        _event(3, "state.updated", {"patch": {"note": None, "extra": 1}}),
        _event(4, "vendor.private", {"ignored": True}),
    ]
    first = project(events)
    second = project(events)
    assert first == second
    assert first["status"] == "running"
    assert first["working_memory"] == {"note": None, "extra": 1}
    assert first["scratchpad"] == [{"role": "user", "content": "a"}]
    assert first["state_version"] == 2


def test_rollback_restores_contents_and_bumps_version():
    events = [
        _event(1, "run.started"),
        _event(
            2,
            "checkpoint.created",
            {
                "checkpoint_id": "ckpt_0001",
                "state_version": 0,
                "snapshot": {"working_memory": {"kept": True}, "scratchpad": []},
            },
        ),
        _event(3, "state.updated", {"patch": {"kept": False, "new": 1}, "scratchpad": [{"role": "tool", "content": "x"}]}),
        _event(4, "recovery.completed", {"action": "rollback", "call_id": "call_0001", "checkpoint_id": "ckpt_0001"}),
    ]
    projected = project(events)
    assert projected["working_memory"] == {"kept": True}
    assert projected["scratchpad"] == []
    assert projected["state_version"] == 2
