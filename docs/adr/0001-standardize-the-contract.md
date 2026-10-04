# ADR 0001 — Standardize the contract, not the implementation

Date: 2026-10-04
Status: accepted

## Context

The proposal is easy to misread as another agent framework. Frameworks answer "build your agent this way." OSAHI has to answer "this is how an execution lifecycle is represented, so two runtimes can be compared and replayed."

If the first code drop is a clever orchestrator with a private object model, the spec will be reverse-engineered from that orchestrator and the initiative will have failed its own test.

## Decision

The normative artifacts are the prose in `spec/` and the JSON Schemas in `schemas/`. The Python package is a reference implementation. Conformance tests accept and reject trajectories as JSON. They do not import harness internals.

A behavior is part of v0.1 only when three things land together:

1. A normative statement that uses RFC 2119 language.
2. A schema or an explicit statement that the rule is semantic and cannot be expressed in JSON Schema alone.
3. A test that fails when the rule is broken.

Reference-only conveniences (the allowlist policy class, the echo tool, the frozen clock) are not requirements on other implementations.

## Consequences

- Features that are hard to observe in the event log do not go into the spec.
- A second runtime, in another language, is a success condition for a later phase, not a distraction from v0.1.
- Pull requests that add a runtime dependency to the spec text should be rewritten so the dependency stays behind an adapter.
