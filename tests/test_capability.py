from osahi.capability import AllowlistPolicy


def test_allowlist_explains_both_effects():
    policy = AllowlistPolicy({"tool.echo"})
    allowed = policy.evaluate("tool.echo")
    denied = policy.evaluate("tool.shell")
    assert allowed == {
        "effect": "allow",
        "reason": "capability is on the allowlist",
        "policy_id": "allowlist",
    }
    assert denied["effect"] == "deny"
    assert denied["reason"]
    assert denied["policy_id"] == "allowlist"
