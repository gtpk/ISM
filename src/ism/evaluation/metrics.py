from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConditionMetric:
    condition: str
    accuracy: float
    accuracy_retention: float | None
    compression_ratio: float | None
    efficiency_score: float | None


def accuracy(values: tuple[bool, ...]) -> float:
    if not values:
        raise ValueError("accuracy requires at least one sample")
    return sum(values) / len(values)


def calculate_condition_metric(
    *,
    condition: str,
    correct: tuple[bool, ...],
    full_correct: tuple[bool, ...],
    compressed_tokens: int,
    full_tokens: int,
) -> ConditionMetric:
    condition_accuracy = accuracy(correct)
    full_accuracy = accuracy(full_correct)
    retention = condition_accuracy / full_accuracy if full_accuracy > 0 else None
    compression_ratio = compressed_tokens / full_tokens if full_tokens > 0 else None
    efficiency = (
        retention / compression_ratio
        if retention is not None and compression_ratio is not None and compression_ratio > 0
        else None
    )
    return ConditionMetric(
        condition=condition,
        accuracy=condition_accuracy,
        accuracy_retention=retention,
        compression_ratio=compression_ratio,
        efficiency_score=efficiency,
    )


def swap_robustness(*, unseen_accuracy: float, original_accuracy: float) -> float | None:
    return unseen_accuracy / original_accuracy if original_accuracy > 0 else None
