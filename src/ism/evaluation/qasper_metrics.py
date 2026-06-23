"""QASPER answer scoring: token-level answer-F1 (Dasigi et al., 2021).

See docs/decisions/0002-qasper-scoring.md. Pure functions, no torch/network.
"""

from __future__ import annotations

import re
import string
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from ism.data.contracts import AnswerRecord, AnswerType

_ARTICLES = re.compile(r"\b(a|an|the)\b")
_PUNCT = str.maketrans("", "", string.punctuation)
# A prediction counts as "no answer" when it normalizes to one of these.
_NO_ANSWER = {"", "unanswerable"}


def normalize(text: str) -> str:
    """SQuAD-style normalization: lowercase, drop punctuation/articles, collapse ws."""
    lowered = text.casefold().translate(_PUNCT)
    no_articles = _ARTICLES.sub(" ", lowered)
    return " ".join(no_articles.split())


def _tokens(text: str) -> list[str]:
    return normalize(text).split()


def token_f1(prediction: str, gold: str) -> float:
    pred_tokens = _tokens(prediction)
    gold_tokens = _tokens(gold)
    if not pred_tokens or not gold_tokens:
        # Both empty -> perfect match; exactly one empty -> no overlap.
        return float(pred_tokens == gold_tokens)
    common = Counter(pred_tokens) & Counter(gold_tokens)
    overlap = sum(common.values())
    if overlap == 0:
        return 0.0
    precision = overlap / len(pred_tokens)
    recall = overlap / len(gold_tokens)
    return 2 * precision * recall / (precision + recall)


def _is_no_answer(prediction: str) -> bool:
    return normalize(prediction) in _NO_ANSWER


def reference_f1(prediction: str, answer: AnswerRecord) -> float:
    if answer.answer_type is AnswerType.UNANSWERABLE:
        return 1.0 if _is_no_answer(prediction) else 0.0
    if _is_no_answer(prediction):
        return 0.0
    return token_f1(prediction, answer.text)


def question_answer_f1(prediction: str, answers: Sequence[AnswerRecord]) -> float:
    """Max token-F1 over a question's reference answers (annotator agreement)."""
    if not answers:
        raise ValueError("question must have at least one reference answer")
    return max(reference_f1(prediction, answer) for answer in answers)


@dataclass(frozen=True)
class QasperScore:
    answer_f1: float
    count: int
    by_type: dict[str, float]


def score_predictions(
    items: Iterable[tuple[str, Sequence[AnswerRecord]]],
) -> QasperScore:
    """Aggregate mean answer-F1 with a per-answer-type breakdown.

    Each item is (prediction, reference answers). An item's type is the type of
    its best-matching reference's first answer, kept simple as the first
    reference's type (QASPER questions are single-type in practice).
    """
    scored: list[tuple[str, float]] = []
    for prediction, answers in items:
        if not answers:
            raise ValueError("question must have at least one reference answer")
        scored.append((answers[0].answer_type.value, question_answer_f1(prediction, answers)))

    if not scored:
        return QasperScore(answer_f1=0.0, count=0, by_type={})

    overall = sum(f1 for _, f1 in scored) / len(scored)
    by_type: dict[str, float] = {}
    for answer_type in sorted({t for t, _ in scored}):
        values = [f1 for t, f1 in scored if t == answer_type]
        by_type[answer_type] = sum(values) / len(values)
    return QasperScore(answer_f1=overall, count=len(scored), by_type=by_type)


__all__ = [
    "QasperScore",
    "normalize",
    "question_answer_f1",
    "reference_f1",
    "score_predictions",
    "token_f1",
]
