from __future__ import annotations

from typing import Protocol


class TokenCounter(Protocol):
    def count(self, text: str) -> int: ...


class WhitespaceTokenCounter:
    def count(self, text: str) -> int:
        return len(text.split())
