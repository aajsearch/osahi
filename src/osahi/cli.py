"""Check a trajectory file, or a reference harness config file.

The trajectory command is unchanged: one JSON list, scored by check_trajectory.
``check-config`` is a reference-runtime convenience and does not call the checker.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from osahi.config import ConfigError, load_config
from osahi.conformance import check_trajectory

_USAGE = "usage: osahi-check <trajectory.json> | osahi-check check-config <file.json>"


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "check-config":
        return _check_config(args[1:])
    if len(args) != 1:
        print(_USAGE, file=sys.stderr)
        return 2
    events = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    violations = check_trajectory(events)
    if violations:
        for violation in violations:
            print(f"{violation['rule']}: {violation['message']}")
        return 1
    print(f"ok {len(events)} events")
    return 0


def _check_config(args: list[str]) -> int:
    if len(args) != 1:
        print("usage: osahi-check check-config <file.json>", file=sys.stderr)
        return 2
    try:
        config = load_config(args[0])
    except ConfigError as exc:
        print(str(exc))
        return 1
    print(f"ok config {config.profile}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
