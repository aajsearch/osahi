"""Model adapter. v0.1 ships a script so tests do not depend on a provider."""

from __future__ import annotations


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
