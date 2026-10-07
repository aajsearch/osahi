# Speaker notes

Walkthrough for the OSAHI talk in osahi.html. These notes are not shown on the slides.

## 1. The layer between the model and the answer

You are looking at the title of the layer that sits between a model and the answer.

OSAHI is the Open Standards Agent Harness Initiative. The large line names where the work lives.

A model proposes the next step. The answer is what comes back after that step is carried out. The layer between them is the execution lifecycle: the run, where a proposal becomes a tool call, a decision, and a result you can keep.

Example: an assistant is asked to book a meeting. The model says to create the event. The lifecycle is where that proposal is checked, the calendar tool is called, and the confirmation is written back. What the person hears is that the meeting is on the calendar.

## 2. The bottleneck moved

Point to the two pictures. On the left, one completion: model, then answer. On the right, a line of ticks: model, tool, state, model, tool, pause, state, tool. The bracket under that line is the execution lifecycle.

The left side is one drop. The right side is where the model comes back after a tool, state is carried forward, and a person can hold the run. The pile-up is that line.

Example: an assistant sending a status message. The model drafts the text. A tool loads the thread. State keeps the draft. The model cuts a sentence. Pause waits until someone confirms the recipient. Then the send tool runs. The answer is only that last step.

## 3. Same model, different run

You are looking at three axes: model, workload, and harness. Runs A and B share a model and a workload and sit apart on the harness. The words above the chart are the private loop: tools, allow or deny, state, retry, pause, and log.

One model, one workload, two harnesses. Move along the harness axis and the run changes.

Example: both runs book Thursday at three, same model, same calendar workload. Harness A denies the invite when the attendee list is empty. Harness B allows it, and the invite goes out with nobody on it.

## 4. The missing record is the run

You are looking at a cross. Exported traces, tool connectivity, agent-to-agent messages, and durable workflows point inward at a dashed center called the run.

Traces stop at what was emitted. Tool connectivity stops at the call. Agent messages stop at the handoff. A durable workflow stops at the process. The dashed center is the shared record of the run.

Example: one assistant messages another to reserve a room. You can show the message, the calendar call, and a completed process. The allow, the timeout, and the state after the room was taken belong in the record at the center.

## 5. What a run must carry

Walk the seven names on the left, then the figure on the right. The model sits above the lifecycle. Tools, memory, and workflow and traces sit below it.

A run carries a run, a trajectory, a capability decision, state, a checkpoint, recovery, and telemetry. The arrow comes down from the model into that box, and three arrows leave it.

Example: an assistant booking a Thursday slot. The run starts. The trajectory keeps each turn. A capability decision allows the calendar and holds mail. State stores the slot. A checkpoint is taken before the write. The calendar times out. Recovery retries from the checkpoint. Telemetry records the timeout. Memory keeps the slot. Workflow and traces receive that same path.

## 6. The path through a run

Walk the seven steps across the top, then the two panels.

A tool call moves from requested to decided. Allow goes on to invoked. Deny goes down, and the call ends. Invoked only after allow.

Recovery is appended after the failure. The failed attempt stays on the record. The three acts are retry, rollback, and escalate. Replay uses the recorded model and tool returns. The model itself is nondeterministic.

Example: an assistant tries to send "Running five minutes late." Send is requested. The decision is deny because the thread id is empty, and the call ends. The next turn hydrates the thread, the decision is allow, and the tool is invoked. The deny stays on the record. Replay plays those recorded returns.

## 7. Challenges the lifecycle names

Four cards.

Vendor lock-in: the loop belongs to one vendor. Context bloat: long runs fill the context until the path fails. Unauditable tool use: a call ran with no decision on the record. Only the final sentence: the path leaked data, corrupted state, or never recovered.

Example: the assistant says, "I sent Maya the agenda." The sentence looks finished. The send had no decision on the record. A private note was still in the body. After a timeout the retry sent it again. The context was full, so the model kept the first story.

## 8. Who builds on it

Start with the assistant orchestrator. Connect a model, hydrate from tools, allow or deny, then answer or reach the goal. The line under it: it books Thursday at three. Calendar is allowed. Mail waits for a person. The same events exist no matter which loop ran.

Then the four roles.

Platform teams run one lifecycle across workloads. One booking workload and one send workload share one record.

Security and audit score a trajectory. They score the deny, then the allow, without reading a private log.

Evaluation compares model, harness, and workload. Same workload, two harnesses, compare the path.

Framework authors emit the same record from their own runtime. They emit those events, and the score still applies.

## 9. What can be shared

The execution record is in the center. A model can be swapped on the left. A tool host can be swapped on the right. The sheet in the middle stays.

Three claims under the figure: a portable execution record, conformance on the path and not only the answer, and the same lifecycle for an independent builder and a large platform.

Example: an assistant books the meeting with one model and one calendar host. You swap the model. You swap the tool host. The record still shows requested, decided, allow, invoked, and the slot written into state. Conformance checks that path.

## 10. Four parts of the lifecycle

Point across the four cards.

Open MCP router: discovery, routing, and authorization for tool endpoints. The reasoning loop does not know where the tool lives.

Virtual memory: scratchpad, episodic cache, and cold storage. Prune the context. Keep the log.

GenAI telemetry: OpenTelemetry semantic conventions on every step. Tokens, latency, the tool sequence, and errors.

Event-sourced orchestrator: an immutable history. Pause and resume. Replay a failure without erasing it.

Example: booking Thursday at three. The calendar call is allowed and mail waits. The scratchpad keeps the slot. The log keeps the timeout. Replay retries from the checkpoint, and the failed attempt stays.

## 11. What is running, and what we standardize

Two columns. Now is what this reference runs today. Standard is what another runtime can share. Point down the four rows.

MCP router. Now, a tool is requested, decided, and invoked only after allow. A remote HTTP tool uses that same path. Standard, any MCP endpoint registers once and the loop does not change. Calendar and mail can move to another service and the decision event stays.

Virtual memory. Now, an L1 scratchpad compacts when the budget overflows, and the trajectory is not shortened. Standard, episodic cache and cold storage are further tiers. Dropped context is summarized, not deleted from the log.

Telemetry. Now, model and tool outcomes carry gen_ai and osahi attributes on the event. Standard, those attributes export through OpenTelemetry without a second schema.

Orchestrator. Now, an append-only log, checkpoints, retry, rollback, escalate, and human pause and resume. Replay uses recorded model and tool returns. Standard, any runtime can fold that log and recover the same way. The failed attempt stays.

Example: the Thursday booking. Send is a second workload on the same record. Calendar is allowed. The timeout is retried. The failed attempt stays on the log.

## 12. Neutral interoperability and reliability across models, tools, and runtimes

Point at the three columns, then the line under them.

Models: swap the model. Tool execution and memory stay. Tools: move calendar or mail to another service. The decision event stays. Runtimes: another loop emits the same record. Recovery and pause still read.

The line under them is reliability: checkpoint, pause, resume, and replay that keeps the failed attempt.

Example: booking Thursday at three. Swap the model. The calendar decision and the timeout retry remain on the record.

## 13. Benefits of the standard

Four lines. Each one is a person from the earlier slide.

An orchestrator debugs the path, not only the final sentence. A platform runs many workloads on one record. Security scores allow and deny without a private log. Evaluation separates the model from the harness on the same workload.

Example: the same Thursday booking. After the model swap, the orchestrator can show the calendar decision and the timeout retry, not only that the meeting is booked. Security scores that path. Evaluation runs the same workload on a second harness.
