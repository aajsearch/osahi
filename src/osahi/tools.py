"""In-process tools. They stand in for MCP or HTTP tools without opening a socket."""

from __future__ import annotations


class EchoTool:
    name = "echo"
    capability_id = "tool.echo"
    idempotent = True

    def invoke(self, arguments: dict) -> dict:
        return {"ok": True, "output": {"text": str(arguments.get("text", ""))}, "error": None}


class AddTool:
    name = "add"
    capability_id = "tool.add"
    idempotent = True

    def invoke(self, arguments: dict) -> dict:
        return {"ok": True, "output": {"sum": arguments["a"] + arguments["b"]}, "error": None}


class FlakyTool:
    """Fails a fixed number of times, then succeeds. Used to make retry visible."""

    def __init__(self, fail_times: int = 1, *, name: str = "flaky", idempotent: bool = True) -> None:
        self.name = name
        self.capability_id = f"tool.{name}"
        self.idempotent = idempotent
        self.fail_times = fail_times
        self.calls = 0

    def invoke(self, arguments: dict) -> dict:
        self.calls += 1
        if self.calls <= self.fail_times:
            return {"ok": False, "output": {}, "error": "transient"}
        return {"ok": True, "output": {"recovered": True}, "error": None}


class DecliningTool:
    """A non-idempotent tool that always fails. Retry must not be chosen for it."""

    name = "charge"
    capability_id = "tool.charge"
    idempotent = False

    def invoke(self, arguments: dict) -> dict:
        return {"ok": False, "output": {}, "error": "declined"}
