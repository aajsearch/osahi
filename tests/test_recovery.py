from osahi.recovery import decide, retries_completed


def test_retry_is_only_for_idempotent_calls_under_the_cap():
    assert decide(idempotent=True, retries_completed=0, checkpoint_exists=True) == "retry"
    assert decide(idempotent=True, retries_completed=1, checkpoint_exists=True) == "retry"
    assert decide(idempotent=True, retries_completed=2, checkpoint_exists=True) == "rollback"
    assert decide(idempotent=False, retries_completed=0, checkpoint_exists=True) == "rollback"
    assert decide(idempotent=False, retries_completed=0, checkpoint_exists=False) == "escalate"


def test_retry_count_reads_the_log_rather_than_a_hidden_counter():
    events = [
        {"type": "recovery.completed", "payload": {"action": "retry", "call_id": "call_0001"}},
        {"type": "recovery.completed", "payload": {"action": "retry", "call_id": "call_0002"}},
        {"type": "recovery.completed", "payload": {"action": "rollback", "call_id": "call_0001"}},
        {"type": "recovery.completed", "payload": {"action": "retry", "call_id": "call_0001"}},
    ]
    assert retries_completed(events, "call_0001") == 2
