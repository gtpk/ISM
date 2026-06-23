from __future__ import annotations

from ism.data.contracts import AnswerRecord, AnswerType
from ism.evaluation.qasper_metrics import (
    normalize,
    question_answer_f1,
    reference_f1,
    score_predictions,
    token_f1,
)


def _answer(text: str, answer_type: AnswerType) -> AnswerRecord:
    return AnswerRecord(text=text, answer_type=answer_type, evidence=())


def test_normalize_strips_articles_punctuation_and_case() -> None:
    assert normalize("The Quick, Brown FOX.") == "quick brown fox"


def test_token_f1_exact_and_partial() -> None:
    assert token_f1("the cat sat", "a cat sat") == 1.0  # articles removed
    assert token_f1("cat dog", "cat") == 2 / 3  # p=1/2, r=1/1
    assert token_f1("cat", "dog") == 0.0


def test_token_f1_empty_cases() -> None:
    assert token_f1("", "") == 1.0
    assert token_f1("cat", "") == 0.0


def test_reference_f1_unanswerable() -> None:
    gold = _answer("Unanswerable", AnswerType.UNANSWERABLE)
    assert reference_f1("Unanswerable", gold) == 1.0
    assert reference_f1("", gold) == 1.0
    assert reference_f1("the model uses BERT", gold) == 0.0


def test_reference_f1_no_answer_against_real_gold_is_zero() -> None:
    gold = _answer("BERT embeddings", AnswerType.ABSTRACTIVE)
    assert reference_f1("unanswerable", gold) == 0.0


def test_question_answer_f1_takes_max_over_references() -> None:
    answers = (
        _answer("graph neural network", AnswerType.ABSTRACTIVE),
        _answer("transformer", AnswerType.ABSTRACTIVE),
    )
    # Exact match against the second reference -> 1.0 despite mismatch with first.
    assert question_answer_f1("Transformer", answers) == 1.0


def test_yes_no_behaves_like_exact_match() -> None:
    gold = (_answer("Yes", AnswerType.YES_NO),)
    assert question_answer_f1("yes", gold) == 1.0
    assert question_answer_f1("No", gold) == 0.0


def test_score_predictions_aggregates_with_type_breakdown() -> None:
    items = [
        ("Transformer", (_answer("transformer", AnswerType.ABSTRACTIVE),)),
        ("Yes", (_answer("Yes", AnswerType.YES_NO),)),
        ("the model uses BERT", (_answer("Unanswerable", AnswerType.UNANSWERABLE),)),
    ]
    score = score_predictions(items)

    assert score.count == 3
    assert score.answer_f1 == (1.0 + 1.0 + 0.0) / 3
    assert score.by_type["abstractive"] == 1.0
    assert score.by_type["yes_no"] == 1.0
    assert score.by_type["unanswerable"] == 0.0
