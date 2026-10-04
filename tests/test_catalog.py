"""Catalog helpers. The fake transport is inspected. The trajectory is not."""

import json

from examples.chat_adapter_echo import main
from osahi.catalog import hosted_chat, http_tool, local_chat

SENTINEL = "sk-osahi-sentinel-key"


def _finish_transport(box: dict):
    def transport(request):
        box["request"] = request
        return {"choices": [{"message": {"role": "assistant", "content": "ok"}}]}

    return transport


def test_hosted_chat_sets_the_authorization_header_on_the_request(monkeypatch):
    monkeypatch.delenv("OSAHI_CHAT_API_KEY", raising=False)
    box: dict = {}
    model = hosted_chat(SENTINEL, "gpt-4o-mini", transport=_finish_transport(box))
    turn = model.next_turn([{"role": "human", "content": "hi"}])
    request = box["request"]
    assert request["url"] == "https://api.openai.com/v1/chat/completions"
    assert request["headers"]["Authorization"] == f"Bearer {SENTINEL}"
    assert request["body"]["model"] == "gpt-4o-mini"
    assert request["body"]["messages"] == [{"role": "user", "content": "hi"}]
    assert SENTINEL not in json.dumps(turn)
    assert SENTINEL not in json.dumps(request["body"])


def test_hosted_chat_reads_the_key_from_the_environment(monkeypatch):
    monkeypatch.setenv("OSAHI_CHAT_API_KEY", SENTINEL)
    box: dict = {}
    model = hosted_chat(model="gpt-4o-mini", transport=_finish_transport(box))
    model.next_turn([])
    assert box["request"]["headers"]["Authorization"] == f"Bearer {SENTINEL}"


def test_local_chat_uses_localhost_and_sends_no_key():
    box: dict = {}
    model = local_chat("llama3", transport=_finish_transport(box))
    model.next_turn([])
    request = box["request"]
    assert request["url"] == "http://127.0.0.1:11434/v1/chat/completions"
    assert "Authorization" not in request["headers"]
    assert request["body"]["model"] == "llama3"


def test_http_tool_helper_posts_json_to_the_given_url():
    seen = {}

    def transport(request):
        seen.update(request)
        return {"status": 200, "body": {"text": "pong"}}

    tool = http_tool("echo", "tool.echo", "http://127.0.0.1:9/echo", transport=transport)
    assert tool.capability_id == "tool.echo"
    assert tool.invoke({"text": "ping"}) == {"ok": True, "output": {"text": "pong"}, "error": None}
    assert seen["url"] == "http://127.0.0.1:9/echo"
    assert seen["body"] == {"text": "ping"}
    assert seen["headers"]["Content-Type"] == "application/json"


def test_example_exits_when_the_key_is_absent(monkeypatch, capsys):
    monkeypatch.delenv("OSAHI_CHAT_API_KEY", raising=False)
    assert main() == 0
    printed = capsys.readouterr().out
    assert "OSAHI_CHAT_API_KEY is absent" in printed
    assert "Fake-transport tests cover the chat adapter path." in printed


def test_example_does_not_print_a_key_when_one_is_set(monkeypatch, capsys):
    monkeypatch.setenv("OSAHI_CHAT_API_KEY", SENTINEL)
    assert main() == 0
    printed = capsys.readouterr().out
    assert SENTINEL not in printed
    assert "hosted chat adapter constructed" in printed
