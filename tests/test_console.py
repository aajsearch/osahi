"""Reference console. The fake transport is the only model I/O."""

import json
import urllib.error
import urllib.request

from osahi.conformance import check_trajectory
from osahi.console import ReferenceConsole, start_console
from osahi.schema import repo_root

SENTINEL = "sk-osahi-sentinel-key"


def _startup_config() -> dict:
    path = repo_root() / "profiles" / "startup.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _request(port: int, method: str, path: str, payload: dict | None = None) -> tuple[int, str]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data is not None else {},
    )
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")


def test_posted_run_conforms_and_the_response_omits_the_api_key():
    seen = {}

    def transport(request):
        seen["authorization"] = request["headers"].get("Authorization")
        seen["url"] = request["url"]
        return {"choices": [{"message": {"role": "assistant", "content": "done"}}]}

    console = ReferenceConsole(transport=transport)
    server = start_console(console)
    try:
        port = server.server_address[1]
        health_status, health_body = _request(port, "GET", "/health")
        assert health_status == 200
        assert json.loads(health_body) == {"ok": True}

        status, body = _request(
            port,
            "POST",
            "/runs",
            {
                "config": _startup_config(),
                "api_key": SENTINEL,
                "base_url": "http://127.0.0.1:9/v1",
            },
        )
        assert status == 200
        assert SENTINEL not in body
        posted = json.loads(body)
        assert posted["status"] == "completed"
        assert posted["violations"] == []
        assert check_trajectory(posted["events"]) == []
        assert seen["authorization"] == f"Bearer {SENTINEL}"
        assert seen["url"] == "http://127.0.0.1:9/v1/chat/completions"

        fetched_status, fetched_body = _request(port, "GET", f"/runs/{posted['run_id']}")
        assert fetched_status == 200
        assert SENTINEL not in fetched_body
        fetched = json.loads(fetched_body)
        assert fetched["status"] == "completed"
        assert fetched["events"] == posted["events"]
        assert fetched["violations"] == []
        assert "api_key" not in fetched
    finally:
        server.shutdown()
        server.server_close()


def test_invalid_config_does_not_call_the_transport_or_echo_the_key():
    def transport(_request):
        raise AssertionError("transport called")

    console = ReferenceConsole(transport=transport)
    server = start_console(console)
    try:
        port = server.server_address[1]
        status, body = _request(
            port,
            "POST",
            "/runs",
            {"config": {"profile": "nope"}, "api_key": SENTINEL},
        )
        assert status == 400
        assert SENTINEL not in body
        assert console.runs == {}
    finally:
        server.shutdown()
        server.server_close()
