from __future__ import annotations

import math
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class ConfidenceInterval:
    estimate: float
    lower: float
    upper: float


def paired_bootstrap_difference(
    first: tuple[float, ...],
    second: tuple[float, ...],
    *,
    seed: int,
    iterations: int = 10_000,
    confidence: float = 0.95,
) -> ConfidenceInterval:
    if len(first) != len(second) or not first:
        raise ValueError("paired bootstrap inputs must be non-empty and aligned")
    if iterations < 1:
        raise ValueError("iterations must be positive")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")
    differences = tuple(a - b for a, b in zip(first, second, strict=True))
    estimate = sum(differences) / len(differences)
    rng = random.Random(seed)
    samples = sorted(
        sum(differences[rng.randrange(len(differences))] for _ in differences) / len(differences)
        for _ in range(iterations)
    )
    alpha = (1 - confidence) / 2
    lower = samples[max(0, math.floor(alpha * iterations))]
    upper = samples[min(iterations - 1, math.ceil((1 - alpha) * iterations) - 1)]
    return ConfidenceInterval(estimate=estimate, lower=lower, upper=upper)


def mcnemar_exact(
    first: tuple[bool, ...],
    second: tuple[bool, ...],
) -> tuple[int, int, float]:
    if len(first) != len(second) or not first:
        raise ValueError("McNemar inputs must be non-empty and aligned")
    first_only = sum(a and not b for a, b in zip(first, second, strict=True))
    second_only = sum(b and not a for a, b in zip(first, second, strict=True))
    discordant = first_only + second_only
    if discordant == 0:
        return first_only, second_only, 1
    tail = sum(
        math.comb(discordant, index) for index in range(min(first_only, second_only) + 1)
    ) / (2**discordant)
    return first_only, second_only, min(1, 2 * tail)


def holm_correction(p_values: tuple[float, ...]) -> tuple[float, ...]:
    if any(not 0 <= value <= 1 for value in p_values):
        raise ValueError("p-values must be in [0, 1]")
    ordered = sorted(enumerate(p_values), key=lambda item: item[1])
    adjusted = [0.0] * len(p_values)
    running = 0.0
    total = len(p_values)
    for rank, (index, value) in enumerate(ordered):
        running = max(running, min(1, value * (total - rank)))
        adjusted[index] = running
    return tuple(adjusted)
