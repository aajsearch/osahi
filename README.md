# OSAHI

**Open Standards Agent Harness Initiative**

OSAHI is an open interoperability and reliability layer for the agent execution lifecycle. It sits between a model and the tools, memory, and runtimes that carry out the model's decisions.

It is not a foundation model, an agent application, or another opinionated agent framework. It does not replace MCP, A2A, OpenTelemetry, or durable workflow engines. It defines the contracts that let those pieces participate in one execution lifecycle, plus a conformance suite and a small reference implementation that prove the contracts are implementable.

The name is the one in the initiating proposal. It names a standards effort — specifications, tests, and replaceable reference code — rather than a product runtime.

## The gap

Production agents have to represent a run, an ordered trajectory, a capability decision, durable state, a checkpoint, a recovery, and telemetry. Today each framework invents its own version of those objects. Swapping the model, the tool host, or the workflow engine means rewriting the loop.

OSAHI standardizes the contract, not the implementation.

## Smallest useful version (0.1)

Seven primitives, and nothing else:

| Primitive | Question it answers |
| --- | --- |
| Agent run | What is one execution, and which model, harness, and workload produced it? |
| Trajectory | What happened, in what order, immutably? |
| Capability | Was this tool call allowed before it ran? |
| State | What is the current projection of the log? |
| Checkpoint | What snapshot can we restore? |
| Recovery | Retry, roll back, or escalate — without deleting history? |
| Telemetry | Which agent-specific fields ride along with each step? |

Version 0.1 records nondeterminism. It does not pretend model outputs are deterministic. Replay rebuilds workflow transitions, authorization decisions, checkpoints, and recovery from the log, using the model and tool results that were recorded at the time.

## What 0.1 deliberately leaves out

- A real MCP router or network proxy
- WASM or microVM isolation (the capability *contract* is in; a sandbox technology is not)
- An OpenTelemetry collector exporter (the semantic attributes are in; a vendor backend is not)
- Tier-2 and tier-3 memory systems (the context lifecycle is specified; only an L1 scratchpad is implemented)
- Bindings to Temporal, Kubernetes, or a hosted control plane

Those belong to later phases. See [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md).

## Layout

```
spec/           normative contracts (RFC 2119 language)
schemas/        JSON Schema for the wire format
conformance/    fixture trajectories the checker must accept or reject
src/osahi/      reference implementation, replaceable by design
tests/          unit tests and conformance tests
examples/       one deterministic echo run
```

## Run the tests

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

No API keys. The reference model is scripted, and the clock and identifiers are injected, so every trajectory is reproducible.

Check a trajectory file:

```bash
python -m osahi.cli conformance/fixtures/allow-echo.json
```
