"""Build the telemetry object carried on model and tool outcome events."""

from __future__ import annotations

from osahi import SPEC_VERSION


def carrier(*, trace_id: str, span_id: str, attributes: dict) -> dict:
    return {"trace_id": trace_id, "span_id": span_id, "attributes": dict(attributes)}


def _base(*, run_id: str, workload_id: str, harness_name: str) -> dict:
    return {
        "osahi.spec.version": SPEC_VERSION,
        "osahi.run.id": run_id,
        "osahi.workload.id": workload_id,
        "osahi.harness.name": harness_name,
    }


def model_attributes(
    *,
    run_id: str,
    workload_id: str,
    harness_name: str,
    model_name: str,
    provider: str,
) -> dict:
    attributes = _base(run_id=run_id, workload_id=workload_id, harness_name=harness_name)
    attributes["gen_ai.operation.name"] = "chat"
    attributes["gen_ai.request.model"] = model_name
    attributes["gen_ai.system"] = provider
    return attributes


def tool_attributes(
    *,
    run_id: str,
    workload_id: str,
    harness_name: str,
    tool_name: str,
    effect: str,
) -> dict:
    attributes = _base(run_id=run_id, workload_id=workload_id, harness_name=harness_name)
    attributes["gen_ai.operation.name"] = "execute_tool"
    attributes["osahi.tool.name"] = tool_name
    attributes["osahi.capability.effect"] = effect
    return attributes
