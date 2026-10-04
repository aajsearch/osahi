"""Construct a hosted chat adapter when OSAHI_CHAT_API_KEY is set.

Without the key this program exits 0. It does not call the network. The
fake-transport tests cover the request and the trajectory.
"""

from __future__ import annotations

import os

from osahi.catalog import CHAT_API_KEY_ENV, hosted_chat


def main() -> int:
    api_key = os.environ.get(CHAT_API_KEY_ENV)
    if not api_key:
        print(
            "OSAHI_CHAT_API_KEY is absent. "
            "Fake-transport tests cover the chat adapter path."
        )
        return 0
    hosted_chat(api_key=api_key, model="gpt-4o-mini", capabilities={"echo": "tool.echo"})
    print("hosted chat adapter constructed. The key stays in the environment.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
