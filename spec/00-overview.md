# OSAHI 0.1 — Overview

Version: 0.1.0
Status: draft for the reference implementation

## Purpose

This specification defines a shared representation of an agent execution lifecycle. An implementation that emits the events in this suite, and passes the conformance checks, can be replayed and compared without adopting the reference runtime.

OSAHI 0.1 standardizes seven primitives:

1. Agent run
2. Trajectory event
3. Capability decision
4. State projection
5. Checkpoint
6. Recovery action
7. Telemetry attributes

## What this specification is not

This specification does not define a foundation model, an agent product, a replacement for MCP, a replacement for A2A, a replacement for OpenTelemetry, a replacement for a durable workflow engine, a vector database, or a sandbox technology.

## Composition

| Existing standard | OSAHI's relationship |
| --- | --- |
| MCP | Tool connectivity. An MCP tool call still passes through `tool.requested` and `capability.decided` before invocation. |
| A2A | Agent-to-agent messages. Out of scope for 0.1. A later event family may reference A2A without changing this envelope. |
| OpenTelemetry | Export substrate. 0.1 defines attribute names carried on events. It does not define an exporter. |
| Durable workflow engines | Persistence and crash recovery. 0.1 defines the events such an engine would store. |

## Vocabulary

| Term | Meaning |
| --- | --- |
| Run | One execution of one workload by one model under one harness. |
| Trajectory | The ordered event log of a run. |
| Harness | The substrate that turns model turns into tool calls, state, and recovery. |
| Workload | The task identity, independent of model and harness. |
| Capability | A named permission to perform an action, typically a tool. |
| Projection | The pure fold of a trajectory into current status and memory. |
| Checkpoint | An event that stores a restorable snapshot. |
| Recovery | An appended action: `retry`, `rollback`, or `escalate`. |

## Requirements language

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are to be interpreted as described in RFC 2119.

## Versioning

`spec_version` on a run MUST equal the document version the emitter implemented. For this document set the value is `0.1.0`. Minor clarifications that do not change event shapes MAY be published as notes. Adding a required field or changing a projection rule requires a new minor version and a conformance update.
