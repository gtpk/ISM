from __future__ import annotations

from ism.representation.leakage import find_leakage


def test_p2_err_002_leakage_validator_detects_question_and_answer() -> None:
    text = "Z1 := What is the final risk?\nZ2 := the answer is HIGH"

    findings = find_leakage(
        text,
        questions=("What is the final risk?",),
        answers=("HIGH",),
    )

    assert {(item.source, item.value) for item in findings} == {
        ("question", "What is the final risk?"),
        ("answer", "HIGH"),
    }


def test_leakage_validator_ignores_absent_values() -> None:
    assert (
        find_leakage(
            "Z1 := marker high",
            questions=("What is the final risk?",),
            answers=("LOW",),
        )
        == ()
    )
