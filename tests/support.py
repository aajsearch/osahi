"""Shared constructors for harness tests. Not part of the wire contract."""

from osahi.capability import AllowlistPolicy
from osahi.clock import FrozenClock
from osahi.harness import ReferenceHarness
from osahi.ids import SequentialIds
from osahi.model import ScriptedModel


def make_harness(*, turns, tools, allowed, budget=8, max_retries=2, recovery_policy=None):
    return ReferenceHarness(
        model=ScriptedModel(turns),
        tools=tools,
        policy=AllowlistPolicy(set(allowed)),
        clock=FrozenClock("2026-10-04T04:30:00Z"),
        ids=SequentialIds(),
        workload={"id": "wl_echo", "name": "echo"},
        model_ref={"provider": "scripted", "name": "fixture-model"},
        context_budget=budget,
        max_retries=max_retries,
        recovery_policy=recovery_policy,
    )
