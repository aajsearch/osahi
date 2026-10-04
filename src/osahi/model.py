"""Model adapters.

``ScriptedModel`` keeps tests off the network. ``ChatCompletionsModel`` speaks
the OpenAI chat-completions protocol to a hosted or local server. Both return
a turn dict from ``next_turn``. Neither appends trajectory events.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from osahi.errors import ModelTransportError


class ScriptedModel:
    def __init__(self, turns: list[dict]) -> None:
        self.turns = turns
        self.index = 0
        self.contexts: list[list[dict]] = []

    def next_turn(self, context: list[dict]) -> dict:
        self.contexts.append([dict(item) for item in context])
        if self.index >= len(self.turns):
            return {"kind": "finish", "text": ""}
        turn = dict(self.turns[self.index])
        self.index += 1
        return turn


# Scratchpad roles the reference harness writes, mapped onto chat messages.
_MESSAGE_ROLES = {
    "human": "user",
    "assistant": "assistant",
    "tool": "user",
    "recovery": "user",
    "user": "user",
    "system": "system",
}


class ChatCompletionsModel:
    """One chat-completions client for a hosted API and for a local server.

    ``transport(request) -> response dict`` is injected so tests never open a
    socket. The default transport uses ``urllib``. ``request`` is
    ``{"url", "method", "headers", "body"}``. When ``api_key`` is non-empty
    the Authorization header is ``Bearer <api_key>`` on that request only.

    ``capabilities`` maps a tool name to a ``capability_id``. A tool call whose
    name is absent becomes a finish turn whose text says the tool is unknown.
    The assistant message is returned as ``raw``. The API key is not copied
    onto the turn.
    """

    def __init__(
        self,
        *,
        model: str,
        base_url: str,
        api_key: str | None = None,
        capabilities: dict[str, str] | None = None,
        transport=None,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or ""
        self.capabilities = dict(capabilities or {})
        self.transport = transport or urllib_chat_transport

    def next_turn(self, context: list[dict]) -> dict:
        request = self._request(context)
        try:
            response = self.transport(request)
        except ModelTransportError:
            raise
        except Exception as exc:
            raise ModelTransportError(f"chat transport failed: {type(exc).__name__}") from exc
        if not isinstance(response, dict):
            raise ModelTransportError("chat transport returned a non-object")
        return self._turn(response)

    def _request(self, context: list[dict]) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        body: dict = {"model": self.model, "messages": _messages(context)}
        if self.capabilities:
            body["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "parameters": {"type": "object", "properties": {}},
                    },
                }
                for name in self.capabilities
            ]
        return {
            "url": f"{self.base_url}/chat/completions",
            "method": "POST",
            "headers": headers,
            "body": body,
        }

    def _turn(self, response: dict) -> dict:
        message = _assistant_message(response)
        raw = _json_object(message)
        content = message.get("content")
        text = content if isinstance(content, str) else ""
        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            return {"kind": "finish", "text": text, "raw": raw}
        call = tool_calls[0] if isinstance(tool_calls[0], dict) else {}
        function = call.get("function") if isinstance(call.get("function"), dict) else call
        name = function.get("name") if isinstance(function, dict) else None
        name = name if isinstance(name, str) else ""
        capability_id = self.capabilities.get(name)
        if not name or capability_id is None:
            return {"kind": "finish", "text": f"unknown tool {name}".strip(), "raw": raw}
        arguments = _arguments(function.get("arguments") if isinstance(function, dict) else None)
        if arguments is None:
            return {
                "kind": "finish",
                "text": f"tool arguments for {name} were not a JSON object",
                "raw": raw,
            }
        return {
            "kind": "tool",
            "text": text,
            "tool_name": name,
            "capability_id": capability_id,
            "arguments": arguments,
            "raw": raw,
        }


def urllib_chat_transport(request: dict) -> dict:
    """POST one chat-completions request. Raises ``ModelTransportError`` on failure."""

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
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise ModelTransportError(f"chat transport failed: HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise ModelTransportError("chat transport failed: unreachable") from exc
    except json.JSONDecodeError as exc:
        raise ModelTransportError("chat transport failed: response was not JSON") from exc


def _messages(context: list[dict]) -> list[dict]:
    messages = []
    for item in context:
        role = _MESSAGE_ROLES.get(item.get("role"), "user")
        content = item.get("content", "")
        if not isinstance(content, str):
            content = json.dumps(content, sort_keys=True)
        messages.append({"role": role, "content": content})
    return messages


def _assistant_message(response: dict) -> dict:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise ModelTransportError("chat transport returned no choices")
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise ModelTransportError("chat transport returned no assistant message")
    return message


def _json_object(value: dict) -> dict:
    try:
        encoded = json.dumps(value)
    except (TypeError, ValueError) as exc:
        raise ModelTransportError("chat transport returned a non-JSON assistant message") from exc
    parsed = json.loads(encoded)
    if not isinstance(parsed, dict):
        raise ModelTransportError("chat transport returned a non-JSON assistant message")
    return parsed


def _arguments(value) -> dict | None:
    if value is None or value == "":
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
    return None
