"""Reference harness. Replaceable. The wire format does not import this module."""

from __future__ import annotations

import copy
import json

from osahi import SPEC_VERSION
from osahi.context import WorkingContext
from osahi.errors import OsahiError
from osahi.log import EventLog
from osahi.project import project
from osahi.recovery import decide as default_decide
from osahi.recovery import retries_completed
from osahi.telemetry import carrier, model_attributes, tool_attributes

_MISSING = object()


class ReferenceHarness:
    def __init__(
        self,
        *,
        model,
        tools,
        policy,
        clock,
        ids,
        workload: dict,
        model_ref: dict,
        harness_ref: dict | None = None,
        context_budget: int = 8,
        max_retries: int = 2,
        recovery_policy=None,
        metadata: dict | None = None,
    ) -> None:
        self.model = model
        self.tools = {tool.name: tool for tool in tools}
        self.policy = policy
        self.clock = clock
        self.ids = ids
        self.workload = dict(workload)
        self.model_ref = dict(model_ref)
        self.harness_ref = dict(harness_ref or {"name": "osahi-reference", "version": "0.1.0"})
        self.max_retries = max_retries
        self.metadata = copy.deepcopy(metadata or {})
        self._decide = recovery_policy or default_decide
        self.context = WorkingContext(context_budget)
        self.log = EventLog()
        self.run: dict | None = None
        self._turn_index = 0
        self._trace_id: str | None = None
        self._last_event_id: str | None = None

    def start(self) -> dict:
        if self.run is not None:
            raise OsahiError("run already started")
        run_id = self.ids.next("run")
        self._trace_id = self.ids.next("trace")
        self.run = {
            "run_id": run_id,
            "spec_version": SPEC_VERSION,
            "status": "created",
            "model": dict(self.model_ref),
            "workload": dict(self.workload),
            "harness": dict(self.harness_ref),
            "created_at": self.clock.now(),
            "parent_run_id": None,
            "metadata": copy.deepcopy(self.metadata),
        }
        self._emit(
            "run.started",
            {
                "spec_version": SPEC_VERSION,
                "model": self.run["model"],
                "workload": self.run["workload"],
                "harness": self.run["harness"],
                "metadata": copy.deepcopy(self.run["metadata"]),
            },
            causation_id=None,
        )
        self._checkpoint()
        return self._export_run()

    def run_until_blocked(self) -> str:
        if self.run is None:
            self.start()
        while self._status() == "running":
            self._one_turn()
        return self._sync_status()

    def resume(self, text: str) -> str:
        if self._status() != "paused":
            raise OsahiError("resume requires a paused run")
        requested = self._latest_event_id("human.requested")
        self._emit("human.responded", {"text": text}, causation_id=requested)
        self._emit("run.resumed", {}, causation_id=self._last_event_id)
        self._remember({"role": "human", "content": text})
        return self.run_until_blocked()

    def events(self) -> list[dict]:
        return self.log.events()

    def projection(self) -> dict:
        return project(self.events())

    def _one_turn(self) -> None:
        turn = self.model.next_turn(self.context.items)
        self._emit("model.invoked", {"turn_index": self._turn_index})
        self._turn_index += 1
        invoked_id = self._last_event_id
        kind = turn["kind"]
        completed = {
            "kind": kind,
            "text": turn.get("text", ""),
            "telemetry": self._model_telemetry(),
        }
        if kind == "tool":
            completed.update(
                {
                    "call_id": self.ids.next("call"),
                    "tool_name": turn["tool_name"],
                    "capability_id": turn["capability_id"],
                    "arguments": copy.deepcopy(turn.get("arguments") or {}),
                }
            )
        self._emit("model.completed", completed, causation_id=invoked_id)
        completed_id = self._last_event_id
        if kind == "finish":
            self._remember({"role": "assistant", "content": turn.get("text", "")})
            self._emit("run.completed", {"text": turn.get("text", "")}, causation_id=completed_id)
            return
        if kind == "human":
            self._emit("human.requested", {"text": turn.get("text", "")}, causation_id=completed_id)
            self._checkpoint()
            self._emit("run.paused", {}, causation_id=self._last_event_id)
            return
        if kind == "tool":
            self._execute_tool(completed, causation_id=completed_id)
            return
        raise OsahiError(f"unknown model kind {kind}")

    def _execute_tool(self, model_payload: dict, *, causation_id: str) -> None:
        call_id = model_payload["call_id"]
        tool_name = model_payload["tool_name"]
        capability_id = model_payload["capability_id"]
        arguments = model_payload["arguments"]
        self._emit(
            "tool.requested",
            {
                "call_id": call_id,
                "tool_name": tool_name,
                "capability_id": capability_id,
                "arguments": arguments,
            },
            causation_id=causation_id,
        )
        decision = self.policy.evaluate(capability_id)
        self._emit(
            "capability.decided",
            {"call_id": call_id, "capability_id": capability_id, **decision},
            causation_id=self._last_event_id,
        )
        if decision["effect"] == "deny":
            self._emit(
                "tool.denied",
                {
                    "call_id": call_id,
                    "tool_name": tool_name,
                    "capability_id": capability_id,
                    "telemetry": self._tool_telemetry(tool_name, "deny"),
                },
                causation_id=self._last_event_id,
            )
            self._remember({"role": "tool", "content": f"denied {tool_name}"})
            return
        self._invoke_until_settled(call_id, tool_name, arguments, causation_id=self._last_event_id)

    def _invoke_until_settled(self, call_id: str, tool_name: str, arguments: dict, *, causation_id: str) -> None:
        cause = causation_id
        while True:
            self._checkpoint()
            self._emit(
                "tool.invoked",
                {"call_id": call_id, "tool_name": tool_name, "arguments": arguments},
                causation_id=cause,
            )
            invoked_id = self._last_event_id
            tool = self.tools.get(tool_name)
            if tool is None:
                result = {"ok": False, "output": {}, "error": f"unknown tool {tool_name}"}
                idempotent = True
            else:
                result = tool.invoke(arguments)
                idempotent = bool(tool.idempotent)
            if result["ok"]:
                self._emit(
                    "tool.completed",
                    {
                        "call_id": call_id,
                        "tool_name": tool_name,
                        "output": result["output"],
                        "telemetry": self._tool_telemetry(tool_name, "allow"),
                    },
                    causation_id=invoked_id,
                )
                self._remember(
                    {"role": "tool", "content": json.dumps(result["output"], sort_keys=True)},
                    patch={call_id: result["output"]},
                )
                return
            self._emit(
                "tool.failed",
                {
                    "call_id": call_id,
                    "tool_name": tool_name,
                    "error": result["error"],
                    "idempotent": idempotent,
                    "telemetry": self._tool_telemetry(tool_name, "allow"),
                },
                causation_id=invoked_id,
            )
            action = self._recovery_action(call_id, idempotent)
            recovery = {"action": action, "call_id": call_id, "reason": result["error"]}
            if action == "rollback":
                recovery["checkpoint_id"] = self._latest_checkpoint_id()
            self._emit("recovery.started", recovery, causation_id=self._last_event_id)
            self._emit("recovery.completed", dict(recovery), causation_id=self._last_event_id)
            if action == "retry":
                cause = self._last_event_id
                continue
            if action == "rollback":
                snapshot = self.projection()["checkpoints"][recovery["checkpoint_id"]]
                self.context.restore(snapshot["scratchpad"])
                self._remember(
                    {"role": "recovery", "content": f"rolled back after {tool_name}: {result['error']}"}
                )
                return
            self._emit("run.failed", {"reason": result["error"]}, causation_id=self._last_event_id)
            return

    def _recovery_action(self, call_id: str, idempotent: bool) -> str:
        projected = self.projection()
        return self._decide(
            idempotent=idempotent,
            retries_completed=retries_completed(self.events(), call_id),
            checkpoint_exists=bool(projected["checkpoints"]),
            max_retries=self.max_retries,
        )

    def _remember(self, item: dict, patch: dict | None = None) -> None:
        compaction = self.context.compaction_for(item)
        if compaction is not None:
            self._emit("context.compacted", compaction, causation_id=self._last_event_id)
        self.context.add(item)
        self._emit(
            "state.updated",
            {
                "patch": patch or {},
                "scratchpad": [dict(entry) for entry in self.context.items],
                "reason": item["role"],
            },
            causation_id=self._last_event_id,
        )

    def _checkpoint(self) -> None:
        projected = self.projection()
        self._emit(
            "checkpoint.created",
            {
                "checkpoint_id": self.ids.next("ckpt"),
                "state_version": projected["state_version"],
                "snapshot": {
                    "working_memory": copy.deepcopy(projected["working_memory"]),
                    "scratchpad": copy.deepcopy(projected["scratchpad"]),
                },
            },
            causation_id=self._last_event_id,
        )

    def _model_telemetry(self) -> dict:
        return carrier(
            trace_id=self._trace_id,
            span_id=self.ids.next("span"),
            attributes=model_attributes(
                run_id=self.run["run_id"],
                workload_id=self.workload["id"],
                harness_name=self.harness_ref["name"],
                model_name=self.model_ref["name"],
                provider=self.model_ref["provider"],
            ),
        )

    def _tool_telemetry(self, tool_name: str, effect: str) -> dict:
        return carrier(
            trace_id=self._trace_id,
            span_id=self.ids.next("span"),
            attributes=tool_attributes(
                run_id=self.run["run_id"],
                workload_id=self.workload["id"],
                harness_name=self.harness_ref["name"],
                tool_name=tool_name,
                effect=effect,
            ),
        )

    def _emit(self, event_type: str, payload: dict, causation_id=_MISSING) -> dict:
        if causation_id is _MISSING:
            causation_id = self._last_event_id
        self.clock.advance()
        stored = self.log.append(
            {
                "event_id": self.ids.next("evt"),
                "run_id": self.run["run_id"],
                "type": event_type,
                "at": self.clock.now(),
                "payload": payload,
                "causation_id": causation_id,
                "correlation_id": self.run["run_id"],
            }
        )
        self._last_event_id = stored["event_id"]
        return stored

    def _latest_checkpoint_id(self) -> str:
        for event in reversed(self.events()):
            if event["type"] == "checkpoint.created":
                return event["payload"]["checkpoint_id"]
        raise OsahiError("no checkpoint to roll back to")

    def _latest_event_id(self, event_type: str) -> str:
        for event in reversed(self.events()):
            if event["type"] == event_type:
                return event["event_id"]
        raise OsahiError(f"missing event {event_type}")

    def _status(self) -> str:
        if self.run is None or not self.log.events():
            return "created"
        return project(self.log.events())["status"]

    def _sync_status(self) -> str:
        status = self._status()
        self.run["status"] = status
        return status

    def _export_run(self) -> dict:
        exported = copy.deepcopy(self.run)
        exported["status"] = self._status()
        return exported
