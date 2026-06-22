from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class LeakageFinding:
    source: str
    value: str


def find_leakage(
    text: str,
    *,
    questions: tuple[str, ...] = (),
    answers: tuple[str, ...] = (),
) -> tuple[LeakageFinding, ...]:
    normalized_text = _normalize(text)
    findings: list[LeakageFinding] = []
    for source, values in (("question", questions), ("answer", answers)):
        for value in values:
            normalized_value = _normalize(value)
            if normalized_value and normalized_value in normalized_text:
                findings.append(LeakageFinding(source=source, value=value))
    return tuple(findings)


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip()
