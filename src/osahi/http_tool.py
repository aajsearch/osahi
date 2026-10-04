"""HTTP tool transport. Stand-in for one MCP tool call.

A later MCP client should implement this same ``invoke(arguments)`` shape,
returning ``{"ok": True, "output": {...}}`` or ``{"ok": False, "error": "..."}``,
and the same name-to-``capability_id`` map ``ChatCompletionsModel`` uses. The
harness still emits ``tool.requested``, then ``capability.decided``, then
``tool.invoked`` only after an allow. This module is the contract for a remote
tool. It is not a second runtime.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request


class HttpTool:
    """POST JSON arguments to ``url``. ``transport`` is injected in tests."""

    def __init__(self, name: str, capability_id: str, url: str, idempotent: bool = True, transport=None) -> None:
        self.name = name
        self.capability_id = capability_id
        self.url = url
        self.idempotent = idempotent
        self.transport = transport or urllib_tool_transport

    def invoke(self, arguments: dict) -> dict:
        request = {
            "url": self.url,
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "body": arguments,
        }
        try:
            response = self.transport(request)
        except Exception as exc:
            return {"ok": False, "output": {}, "error": f"{type(exc).__name__}: {exc}"}
        if not isinstance(response, dict):
            return {"ok": False, "output": {}, "error": "tool transport returned a non-object"}
        status = response.get("status", 0)
        body = response.get("body")
        try:
            code = int(status)
        except (TypeError, ValueError):
            return {"ok": False, "output": {}, "error": "tool transport returned no status"}
        if 200 <= code < 300:
            if isinstance(body, dict):
                return {"ok": True, "output": body, "error": None}
            return {"ok": True, "output": {"value": body}, "error": None}
        error = f"HTTP {code}"
        if isinstance(body, dict) and isinstance(body.get("error"), str) and body["error"]:
            error = body["error"]
        return {"ok": False, "output": {}, "error": error}


def urllib_tool_transport(request: dict) -> dict:
    """POST a tool body. HTTP error statuses are returned, not raised."""

    payload = json.dumps(request["body"]).encode("utf-8")
    headers = {str(key): str(value) for key, value in (request.get("headers") or {}).items()}
    outgoing = urllib.request.Request(
        request["url"],
        data=payload,
        headers=headers,
        method=request.get("method") or "POST",
    )
    try:
        with urllib.request.urlopen(outgoing, timeout=30) as response:
            return {"status": response.status, "body": _read_body(response)}
    except urllib.error.HTTPError as exc:
        return {"status": exc.code, "body": _read_body(exc)}


def _read_body(response) -> object:
    raw = response.read().decode("utf-8")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"value": raw}
