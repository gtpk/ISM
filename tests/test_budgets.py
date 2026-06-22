from __future__ import annotations

from dataclasses import replace

import pytest

from ism.data.generator import GeneratedDocument, SyntheticGenerator
from ism.experiments.budgets import (
    BudgetArtifact,
    DeterministicRepresentationProducer,
    RepresentationProducer,
    audit_budget_matrix,
    budget_matrix_digest,
    build_budget_matrix,
)
from ism.representation.tokenizer import WhitespaceTokenCounter


class OversizedProducer:
    def __init__(self) -> None:
        self.calls = 0

    def produce(
        self,
        document: GeneratedDocument,
        *,
        method: str,
        budget: int,
        attempt: int,
    ) -> str:
        del document, method, attempt
        self.calls += 1
        return " ".join("token" for _ in range(budget + 1))


def build(
    *,
    methods: tuple[str, ...] = ("ism", "model_summary"),
    budgets: tuple[int, ...] = (128, 256),
    producer: RepresentationProducer | None = None,
    max_attempts: int = 3,
) -> tuple[BudgetArtifact, ...]:
    tokenizer = WhitespaceTokenCounter()
    return build_budget_matrix(
        SyntheticGenerator(42).generate(2),
        methods=methods,
        budgets=budgets,
        tokenizer=tokenizer,
        tokenizer_revision="whitespace-v1",
        max_attempts=max_attempts,
        producer=producer or DeterministicRepresentationProducer(tokenizer, seed=42),
    )


def test_p5_cfg_001_all_methods_use_the_same_budget_set() -> None:
    artifacts = build()
    by_method = {
        method: {item.budget for item in artifacts if item.method == method}
        for method in {item.method for item in artifacts}
    }

    assert set(map(frozenset, by_method.values())) == {frozenset({128, 256})}


def test_p5_fun_001_every_valid_artifact_is_within_budget() -> None:
    artifacts = build()

    assert all(item.token_count <= item.budget for item in artifacts if item.valid)


def test_p5_fun_002_counts_representation_without_external_prompt() -> None:
    artifacts = build(methods=("model_summary",), budgets=(8,))

    assert all(item.token_count == len(item.text.split()) for item in artifacts)
    assert all("prompt" not in item.text for item in artifacts)


def test_p5_fun_003_budget_failure_stops_at_max_attempts() -> None:
    producer = OversizedProducer()

    artifacts = build(
        methods=("ism",),
        budgets=(4,),
        producer=producer,
        max_attempts=3,
    )

    assert producer.calls == 6
    assert all(not item.valid for item in artifacts)
    assert all(item.attempts == 3 for item in artifacts)
    assert all(item.error == "budget_exceeded: 5 > 4" for item in artifacts)


def test_p5_con_001_mixed_tokenizer_revision_is_rejected() -> None:
    artifacts = build(methods=("ism",), budgets=(128,))
    damaged = (replace(artifacts[0], tokenizer_revision="other"), *artifacts[1:])

    with pytest.raises(ValueError, match="tokenizer revisions"):
        audit_budget_matrix(
            damaged,
            document_ids={item.document_id for item in artifacts},
            methods=("ism",),
            budgets=(128,),
            tokenizer_revision="whitespace-v1",
        )


def test_p5_con_002_method_budget_matrix_has_no_missing_combination() -> None:
    artifacts = build()

    with pytest.raises(ValueError, match="missing"):
        audit_budget_matrix(
            artifacts[:-1],
            document_ids={item.document_id for item in artifacts},
            methods=("ism", "model_summary"),
            budgets=(128, 256),
            tokenizer_revision="whitespace-v1",
        )


def test_p5_reg_001_whitespace_token_count_golden() -> None:
    tokenizer = WhitespaceTokenCounter()

    assert tokenizer.count("Z1 Z2 !Z3 => HIGH") == 5
    assert budget_matrix_digest(build(methods=("ism",), budgets=(128,))) == (
        "43d080da51da7face4ef58bc76823e61d5d540161da051f50e78e9fd67023b34"
    )
