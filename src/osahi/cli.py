"""Check a trajectory file against the v0.1 conformance rules."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from osahi.conformance import check_trajectory


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("usage: osahi-check <trajectory.json>", file=sys.stderr)
        return 2
    events = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    violations = check_trajectory(events)
    if violations:
        for violation in violations:
            print(f"{violation['rule']}: {violation['message']}")
        return 1
    print(f"ok {len(events)} events")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
