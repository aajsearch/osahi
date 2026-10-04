# ADR 0003 — Record nondeterminism instead of requiring deterministic models

Date: 2026-10-04
Status: accepted

## Context

The proposal asks for replay and also admits that model outputs and external systems are not deterministic. Treating "deterministic execution" as a requirement would either exclude every real model or encourage harnesses to hide nondeterminism behind caches that no one can inspect.

What debugging actually needs is narrower:

- The same event order
- The same authorization decisions
- The same checkpoint contents
- The same recovery choice
- The model output and tool response that were observed, stored on the event

## Decision

Replay is a fold over the log. `project(events)` MUST be a pure function of those events. It MUST NOT call a model or a tool.

The reference harness calls the model and the tools once, while the run is live, and writes the observed output onto `model.completed` and `tool.completed` / `tool.failed`. A later replay reads those payloads.

Timestamps are informational. `seq` is the order. Tests inject a clock so live runs are reproducible, but conformance MUST NOT require equal timestamps across implementations.

The v0.1 reference model is scripted so CI can run without a provider. The script is a stand-in for a recorded model, not a claim that production models are scripts.

## Consequences

- Two runs of a nondeterministic model are allowed to differ. Comparison happens at the trajectory-invariant layer (Phase D), not by hashing final text.
- Provider adapters, when they arrive, must persist the raw model turn on the event before the harness acts on it.
- A test that mocks the clock is required. A test that calls a live model is out of scope for v0.1.
