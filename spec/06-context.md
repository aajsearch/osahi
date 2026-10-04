# Context lifecycle

Version: 0.1.0

## Role

Working context is the material the harness places in front of the model. It is not the trajectory. The trajectory is complete. The context is a bounded view, because prompt growth dominates cost and reliability on long runs.

## Tiers

| Tier | Name | 0.1 status |
| --- | --- | --- |
| L1 | Scratchpad | Specified and implemented. |
| L2 | Episodic cache | Named only. No event types, no reference code. |
| L3 | Cold storage | Named only. No event types, no reference code. |

A future tier MUST be introduced by new event types or new optional payload fields. It MUST NOT change the meaning of `context.compacted` or of scratchpad items.

## Scratchpad item

```json
{ "role": "summary", "content": "compacted 3 items" }
```

`role` and `content` MUST be strings. Emitters MAY add additional keys.

## Budget

The reference harness limits the scratchpad by item count. The count is emitter policy and MUST NOT be required to equal any particular number by conformance.

When accepting a new item would exceed the budget, the emitter MUST:

1. Choose a non-empty prefix of the oldest items to drop, enough that the retained list plus a summary item plus the new item fits the budget. If the budget is 1, the retained list is the summary item alone and the new item replaces it on the following state update only when the budget allows; the reference budget MUST be at least 2 so a summary and a new item can coexist. The reference implementation uses a caller-supplied budget that tests set at 2 or higher.
2. Append `context.compacted` with `dropped` (integer, the count removed) and `retained` (the new scratchpad, beginning with one summary item whose content reports how many items were compacted).
3. Append the new item through the ordinary state path (`state.updated` with the extended scratchpad).

`context.compacted` is the audit record that context was reduced. A consumer MUST be able to detect compaction without diffing prompts.

## What is not compacted

The trajectory MUST NOT be shortened when context is compacted. Compaction changes the scratchpad projection only.

## Model-facing context

The reference harness sends the current scratchpad to the model adapter. Adapters MAY format items as vendor messages. That formatting is not part of the wire contract. What the model *returned* is part of the contract, on `model.completed`.
