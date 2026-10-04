# Telemetry

Version: 0.1.0

## Role

Agent telemetry describes model calls, tool calls, capability decisions, checkpoints, and recovery. OpenTelemetry is the intended export path. This document defines the attributes OSAHI requires on the event. It does not define a collector, an exporter, or a vendor backend.

## Carrier

Outcome events carry:

```json
"telemetry": {
  "trace_id": "trace_0001",
  "span_id": "span_0004",
  "attributes": {}
}
```

`trace_id` MUST be stable for all events in a run. `span_id` MUST be unique within the run. Both are opaque strings.

Events that MUST include `telemetry`:

- `model.completed`
- `tool.completed`
- `tool.failed`
- `tool.denied`

Other events MAY include it.

## Attributes required on every telemetry carrier

| Attribute | Rule |
| --- | --- |
| `osahi.spec.version` | Equal to the run's `spec_version`. |
| `osahi.run.id` | Equal to `run_id`. |
| `osahi.workload.id` | Equal to the workload id. |
| `osahi.harness.name` | Equal to the harness name. |
| `gen_ai.operation.name` | `chat` for model events, `execute_tool` for tool events. |

## Model events

`model.completed` attributes MUST also include:

| Attribute | Rule |
| --- | --- |
| `gen_ai.request.model` | The model `name` from the run. |
| `gen_ai.system` | The model `provider` from the run. |

## Tool events

`tool.completed`, `tool.failed`, and `tool.denied` attributes MUST also include:

| Attribute | Rule |
| --- | --- |
| `osahi.tool.name` | Tool name. |
| `osahi.capability.effect` | `allow` or `deny`. Denial events MUST use `deny`. Completed and failed events MUST use `allow`. |

## Names

Attributes already established by GenAI semantic conventions use those names (`gen_ai.operation.name`, `gen_ai.request.model`, `gen_ai.system`). Attributes that are specific to this lifecycle use the `osahi.` prefix.

An exporter MAY rename attributes at the boundary. The trajectory MUST keep the names in this document so two implementations can be compared before any exporter runs.

## Non-requirements

0.1 does NOT require span parent pointers, exemplars, metrics, or log export. A `trace_id` plus ordered `span_id`s is enough to prove that every tool and model outcome is observable.
