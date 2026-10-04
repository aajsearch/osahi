"""L1 scratchpad. Compaction shortens what the model sees and never the log."""

from __future__ import annotations


class WorkingContext:
    def __init__(self, budget: int) -> None:
        if budget < 2:
            raise ValueError("scratchpad budget must be at least 2 so a summary and a new item can coexist")
        self.budget = budget
        self.items: list[dict] = []

    def compaction_for(self, _incoming: dict) -> dict | None:
        """Return a compaction payload when the incoming item would overflow.

        The retained list does not yet include the incoming item. The caller appends
        that item on the following state update.
        """

        if len(self.items) + 1 <= self.budget:
            return None
        keep = self.budget - 2
        dropped = len(self.items) - keep
        retained = [
            {"role": "summary", "content": f"compacted {dropped} items"},
            *self.items[dropped:],
        ]
        self.items = [dict(item) for item in retained]
        return {"dropped": dropped, "retained": [dict(item) for item in self.items]}

    def add(self, item: dict) -> None:
        self.items.append(dict(item))

    def restore(self, items: list[dict]) -> None:
        self.items = [dict(item) for item in items]
