"""Short reference catalog. One hosted chat, one local chat, one HTTP tool.

Credentials come from arguments or, for the hosted helper only, from
``OSAHI_CHAT_API_KEY``. This module does not log a key and does not write one
into a config file. Further tools belong in separate packages.
"""

from __future__ import annotations

import os

from osahi.http_tool import HttpTool
from osahi.model import ChatCompletionsModel

CHAT_API_KEY_ENV = "OSAHI_CHAT_API_KEY"


def hosted_chat(
    api_key: str | None = None,
    model: str = "gpt-4o-mini",
    base_url: str = "https://api.openai.com/v1",
    *,
    capabilities: dict[str, str] | None = None,
    transport=None,
) -> ChatCompletionsModel:
    """Chat completions against a hosted server. ``api_key`` wins over the environment."""

    if api_key is None:
        api_key = os.environ.get(CHAT_API_KEY_ENV)
    return ChatCompletionsModel(
        model=model,
        base_url=base_url,
        api_key=api_key,
        capabilities=capabilities,
        transport=transport,
    )


def local_chat(
    model: str,
    base_url: str = "http://127.0.0.1:11434/v1",
    *,
    capabilities: dict[str, str] | None = None,
    transport=None,
) -> ChatCompletionsModel:
    """The same chat adapter against a local server. No API key is required."""

    return ChatCompletionsModel(
        model=model,
        base_url=base_url,
        api_key=None,
        capabilities=capabilities,
        transport=transport,
    )


def http_tool(name: str, capability_id: str, url: str, idempotent: bool = True, *, transport=None) -> HttpTool:
    """One remote tool. A deny still prevents ``invoke`` from calling ``transport``."""

    return HttpTool(name, capability_id, url, idempotent=idempotent, transport=transport)
