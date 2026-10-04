# Capability

Version: 0.1.0

## Role

A capability is the permission to perform an action. In 0.1 the only action is a tool call. The spec standardizes the decision record, not the policy language and not the isolation technology that enforces it.

## Path

For each tool call identified by `call_id`, a conforming trajectory MUST follow this order:

1. `tool.requested`
2. `capability.decided` with the same `call_id`
3. Either:
   - `effect = allow`, then `tool.invoked` with that `call_id`, then `tool.completed` or `tool.failed`; or
   - `effect = deny`, then `tool.denied` with that `call_id`, and no `tool.invoked` for that `call_id` anywhere later in the trajectory.

A trajectory that contains `tool.invoked` without a prior `allow` for the same `call_id` is non-conformant.

A trajectory that contains `tool.invoked` after a `deny` for the same `call_id` is non-conformant.

## Decision object

| Field | Rule |
| --- | --- |
| `effect` | MUST be `allow` or `deny`. |
| `reason` | Human-readable. MUST be non-empty. |
| `policy_id` | Identifies the policy that decided. Opaque. |
| `capability_id` | MUST equal the id on the matching `tool.requested`. |

## Policy

The reference policy is an allowlist of `capability_id` values. An implementation MAY use any policy that emits the decision event before invocation. Conformance MUST NOT require the allowlist.

## Constraints

A decision MAY include `constraints`, an object whose keys are implementation-defined (`network`, `filesystem`, and similar). 0.1 does not require a sandbox to enforce them. A later profile MAY. Adding enforcement MUST NOT remove the decision event.

## Audit

The decision event is the audit record. Implementations MUST NOT authorize a tool only in memory and omit `capability.decided`.
