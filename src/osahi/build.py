"""Assemble a ReferenceHarness from config plus in-process adapters.

Tools are code, so they are passed in rather than read from JSON. A capability
id in ``policy.allow`` with no tool is legal: the id may be reserved for a
tool that is not registered in this process. A tool whose ``capability_id``
is absent from the allow list is also legal at build time. The allowlist
denies that call when it is attempted, and the harness records ``tool.denied``
instead of ``tool.invoked``.
"""

from __future__ import annotations

from osahi.capability import AllowlistPolicy
from osahi.clock import FrozenClock
from osahi.config import ConfigError, HarnessConfig
from osahi.harness import ReferenceHarness
from osahi.ids import SequentialIds

_REFERENCE_INSTANT = "2026-10-04T04:30:00Z"


def build_harness(
    config: HarnessConfig,
    *,
    tools,
    model,
    clock=None,
    ids=None,
    recovery_policy=None,
    policy=None,
) -> ReferenceHarness:
    """Wire the reference loop. The caller supplies tools and a model adapter."""

    if not isinstance(config, HarnessConfig):
        raise ConfigError([("<root>", "build_harness expects a HarnessConfig from load_config")])
    if config.recovery.checkpoints is not True:
        raise ConfigError([("recovery.checkpoints", "checkpoints must stay enabled")])
    if config.telemetry.enabled is not True:
        raise ConfigError([("telemetry.enabled", "telemetry must stay enabled")])
    installed = policy if policy is not None else AllowlistPolicy(
        set(config.policy.allow),
        policy_id=config.policy.policy_id,
    )
    return ReferenceHarness(
        model=model,
        tools=list(tools),
        policy=installed,
        clock=clock or FrozenClock(_REFERENCE_INSTANT),
        ids=ids or SequentialIds(),
        workload={"id": config.workload.id, "name": config.workload.name},
        model_ref={"provider": config.model.provider, "name": config.model.name},
        harness_ref={"name": config.harness.name, "version": config.harness.version},
        context_budget=config.context.budget,
        max_retries=config.recovery.max_retries,
        recovery_policy=recovery_policy,
        metadata=dict(config.metadata),
    )
