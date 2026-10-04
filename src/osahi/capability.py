"""Reference allowlist policy. The spec requires a decision event, not this policy."""

from __future__ import annotations


class AllowlistPolicy:
    def __init__(self, allowed: set[str], policy_id: str = "allowlist") -> None:
        self.allowed = set(allowed)
        self.policy_id = policy_id

    def evaluate(self, capability_id: str) -> dict:
        if capability_id in self.allowed:
            effect = "allow"
            reason = "capability is on the allowlist"
        else:
            effect = "deny"
            reason = "capability is not on the allowlist"
        return {"effect": effect, "reason": reason, "policy_id": self.policy_id}
