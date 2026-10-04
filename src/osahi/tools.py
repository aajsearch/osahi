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


class ToolSpec:
    """A function registered as a tool the reference harness already knows how to call.

    ``fn`` receives the argument object. A returned dict is the tool output.
    A dict that already contains ``ok`` is treated as a full tool result.
    Any other return value is wrapped as ``{"value": ...}``. An exception
    becomes a failed result so the harness can recover instead of crashing.
    """

    def __init__(self, name: str, capability_id: str, fn, idempotent: bool = True) -> None:
        self.name = name
        self.capability_id = capability_id
        self.fn = fn
        self.idempotent = idempotent

    def invoke(self, arguments: dict) -> dict:
        try:
            result = self.fn(arguments)
        except Exception as exc:
            return {"ok": False, "output": {}, "error": f"{type(exc).__name__}: {exc}"}
        if isinstance(result, dict) and "ok" in result:
            output = result.get("output", {})
            if not isinstance(output, dict):
                output = {"value": output}
            return {"ok": bool(result["ok"]), "output": output, "error": result.get("error")}
        if isinstance(result, dict):
            return {"ok": True, "output": result, "error": None}
        return {"ok": True, "output": {"value": result}, "error": None}


class DecliningTool:
    """A non-idempotent tool that always fails. Retry must not be chosen for it."""

    name = "charge"
    capability_id = "tool.charge"
    idempotent = False

    def invoke(self, arguments: dict) -> dict:
        return {"ok": False, "output": {}, "error": "declined"}
