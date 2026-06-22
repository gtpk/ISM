from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvaluationPrediction:
    run_id: str
    question_id: str
    condition: str
    correct: bool

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.run_id, self.question_id, self.condition)


def audit_predictions(
    predictions: tuple[EvaluationPrediction, ...],
    *,
    conditions: tuple[str, ...],
) -> None:
    keys = [item.key for item in predictions]
    if len(keys) != len(set(keys)):
        raise ValueError("prediction keys must be unique")
    by_condition = {
        condition: {item.question_id for item in predictions if item.condition == condition}
        for condition in conditions
    }
    if len(set(map(frozenset, by_condition.values()))) > 1:
        raise ValueError("paired conditions do not have identical question sets")
