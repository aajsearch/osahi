"""Reference console. A client of the contract, not the standard.

It loads a harness config, starts one in-memory run, and returns the trajectory
plus ``check_trajectory`` violations. There is no account system and no database.
``api_key`` is read from the request body and passed to ``ChatCompletionsModel``.
It is not written to a config file and it is not stored on the run.

Pass ``transport``. Tests pass a fake. ``urllib_chat_transport`` is opt-in for a
live process. The default does not open a socket.
"""

from __future__ import annotations

import copy
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from osahi.build import build_harness
from osahi.config import ConfigError, load_config
from osahi.conformance import check_trajectory
from osahi.errors import OsahiError
from osahi.ids import SequentialIds
from osahi.model import ChatCompletionsModel

_MAX_BODY = 1_000_000


class ReferenceConsole:
    """In-memory runs. ``transport`` is required so this process stays offline in tests."""

    def __init__(self, *, transport, tools=None) -> None:
        if transport is None:
            raise OsahiError("console transport is required")
        self.transport = transport
        self.tools = list(tools or [])
        self.ids = SequentialIds()
        self.runs: dict[str, dict] = {}

    def start_run(self, document: dict) -> dict:
        if not isinstance(document, dict):
            raise ConfigError([("<root>", "POST /runs requires a JSON object")])
        api_key = document.get("api_key")
        if api_key is not None and not isinstance(api_key, str):
            raise ConfigError([("api_key", "api_key must be a string")])
        config_doc = document.get("config")
        if not isinstance(config_doc, dict):
            raise ConfigError([("config", "config must be a JSON object")])
        config_doc = copy.deepcopy(config_doc)
        config_doc.pop("api_key", None)
        metadata = config_doc.get("metadata")
        if isinstance(metadata, dict):
            metadata.pop("api_key", None)
            metadata.pop("authorization", None)
        config = load_config(config_doc)
        base_url = document.get("base_url") or "http://127.0.0.1:9/v1"
        if not isinstance(base_url, str) or not base_url:
            raise ConfigError([("base_url", "base_url must be a string")])
        capabilities = document.get("capabilities") or {}
        if not isinstance(capabilities, dict):
            raise ConfigError([("capabilities", "capabilities must be an object")])
        model = ChatCompletionsModel(
            model=config.model.name,
            base_url=base_url,
            api_key=api_key if isinstance(api_key, str) else None,
            capabilities={str(name): str(capability) for name, capability in capabilities.items()},
            transport=self.transport,
        )
        harness = build_harness(config, tools=self.tools, model=model, ids=self.ids)
        status = harness.run_until_blocked()
        events = harness.events()
        record = {
            "run_id": harness.run["run_id"],
            "status": status,
            "events": events,
            "violations": check_trajectory(events),
        }
        self.runs[record["run_id"]] = record
        return record


class ConsoleServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, console: ReferenceConsole) -> None:
        self.console = console
        super().__init__(address, ConsoleHandler)


class ConsoleHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/health":
            self._send(200, {"ok": True})
            return
        if path.startswith("/runs/"):
            run_id = path[len("/runs/") :]
            record = self.server.console.runs.get(run_id)
            if record is None:
                self._send(404, {"error": "run not found"})
                return
            self._send(200, record)
            return
        self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path.split("?", 1)[0] != "/runs":
            self._send(404, {"error": "not found"})
            return
        try:
            document = json.loads(self._read_body().decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            self._send(400, {"error": "body must be JSON"})
            return
        try:
            record = self.server.console.start_run(document)
        except ConfigError as exc:
            self._send(400, {"error": str(exc)})
            return
        self._send(200, record)

    def log_message(self, fmt, *args) -> None:
        return

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length > _MAX_BODY:
            raise ValueError("body is too large")
        if length < 0:
            raise ValueError("body must be JSON")
        return self.rfile.read(length) if length else b""

    def _send(self, status: int, payload: dict) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def start_console(console: ReferenceConsole, host: str = "127.0.0.1", port: int = 0) -> ConsoleServer:
    """Bind an ephemeral port when ``port`` is 0 and serve until ``shutdown``."""

    server = ConsoleServer((host, port), console)
    thread = threading.Thread(target=server.serve_forever, name="osahi-console", daemon=True)
    thread.start()
    server.serve_thread = thread
    return server
