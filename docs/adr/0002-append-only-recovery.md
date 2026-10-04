# ADR 0002 — Recovery appends events and never rewrites the log

Date: 2026-10-04
Status: accepted

## Context

Agent loops fail in ordinary ways: a tool times out, a rate limit hits, a human needs to approve, a process restarts. Durable workflow engines already solve process recovery. OSAHI still has to say what an *agent* recovery means in the trajectory.

Two designs compete.

- Mutable state: store the latest memory, and on failure overwrite it with a checkpoint. The log, if any, is an optimization.
- Append-only: the log is the source of truth. Retry, rollback, and escalation are new events. A projection folds the log into current memory.

The mutable design is shorter to code and impossible to audit. After a rollback, the denied call or the failed attempt is gone, so a conformance test cannot prove it happened.

## Decision

`EventLog` has append and read. It has no update and no delete.

Rollback restores snapshot contents into the projection and increments `state_version`. The version counter is monotonic so consumers can detect a restore without diffing memory.

Retry does not call the model again. The original `model.completed` event remains the authority for which tool was requested. The new events record the additional attempt.

Escalate appends `run.failed` and stops the lifecycle. It does not erase the failure that caused it.

## Consequences

- Checkpoints must carry enough snapshot to restore contents, because the projection will not "undo" individual patches in place.
- Logs grow with retries. That growth is the audit trail. Compaction of the *prompt* (ADR context lifecycle) is separate from compaction of the *log*. The log is not compacted in v0.1.
- A crash-safe store in a later phase persists the same events. It does not introduce a second history.
