# Agent run

Version: 0.1.0

## Role

An agent run is the unit of execution that binds a model, a harness, and a workload. Evaluation that ignores any of the three attributes a result to the wrong cause.

## Wire object

A run object MUST contain:

| Field | Type | Rule |
| --- | --- | --- |
| `run_id` | string | Unique within an emitter. Opaque. |
| `spec_version` | string | MUST be `0.1.0` for this version. |
| `status` | string | One of `created`, `running`, `paused`, `completed`, `failed`, `cancelled`. |
| `model` | object | MUST contain `provider` and `name`. |
| `workload` | object | MUST contain `id` and `name`. |
| `harness` | object | MUST contain `name` and `version`. |
| `created_at` | string | ISO-8601 UTC, suffix `Z`. |
| `parent_run_id` | string or null | MUST be null in 0.1. Reserved for child runs. |
| `metadata` | object | Emitter-defined. MUST be a JSON object. MUST NOT be required for conformance. |

The reference emitter uses `model.provider = scripted` when the turn source is a fixture. Other providers MAY appear. Conformance MUST NOT require a specific provider.

## Status machine

```
created → running → paused → running → completed
                  ↘ failed
                  ↘ cancelled
```

- The run object is created with status `created`.
- The first trajectory event MUST be `run.started`, which moves status to `running`.
- `run.paused` is legal only from `running`.
- `run.resumed` is legal only from `paused`.
- `run.completed`, `run.failed`, and `run.cancelled` are terminal.
- An implementation MUST NOT append a lifecycle event after a terminal lifecycle event.

Status on the run object and status implied by the trajectory MUST agree after each event is applied. The trajectory is authoritative. A stored run object is a cache of the projection.

## Identity of the triad

Two runs that share a `workload.id` and differ in `model` or `harness` are different runs. Implementations MUST NOT reuse a `run_id` across those executions. Comparison across the triad is a consumer concern; the spec only requires that the three references are present and stable for the life of the run.
