from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Protocol

from ism.data.generator import GeneratedDocument
from ism.experiments.conditions import build_condition_matrix
from ism.representation.tokenizer import TokenCounter


class RepresentationProducer(Protocol):
    def produce(
        self,
        document: GeneratedDocument,
        *,
        method: str,
        budget: int,
        attempt: int,
    ) -> str: ...


@dataclass(frozen=True)
class BudgetArtifact:
    document_id: str
    method: str
    budget: int
    tokenizer_revision: str
    text: str
    token_count: int
    attempts: int
    valid: bool
    error: str | None

    @property
    def key(self) -> tuple[str, str, int]:
        return (self.document_id, self.method, self.budget)


class DeterministicRepresentationProducer:
    def __init__(self, tokenizer: TokenCounter, *, seed: int) -> None:
        self.tokenizer = tokenizer
        self.seed = seed

    def produce(
        self,
        document: GeneratedDocument,
        *,
        method: str,
        budget: int,
        attempt: int,
    ) -> str:
        del attempt
        condition = {
            "ism": "full_symbol_dict",
            "model_summary": "model_summary",
            "keyword_extract": "keyword_extract",
            "llmlingua_2": "llmlingua_2",
        }.get(method)
        if condition is None:
            raise ValueError(f"unsupported budget method: {method}")
        matrix = build_condition_matrix(
            (document,),
            conditions=(condition,),  # type: ignore[arg-type]
            budget=budget,
            seed=self.seed,
            tokenizer=self.tokenizer,
        )
        return matrix.compressions[0].serialized_text


def build_budget_matrix(
    documents: tuple[GeneratedDocument, ...],
    *,
    methods: tuple[str, ...],
    budgets: tuple[int, ...],
    tokenizer: TokenCounter,
    tokenizer_revision: str,
    max_attempts: int,
    producer: RepresentationProducer,
) -> tuple[BudgetArtifact, ...]:
    if not methods or len(methods) != len(set(methods)):
        raise ValueError("methods must be non-empty and unique")
    if not budgets or len(budgets) != len(set(budgets)) or any(item < 1 for item in budgets):
        raise ValueError("budgets must be positive and unique")
    if not tokenizer_revision:
        raise ValueError("tokenizer_revision must not be empty")
    if max_attempts < 1:
        raise ValueError("max_attempts must be positive")

    artifacts = tuple(
        _generate_with_budget(
            document,
            method=method,
            budget=budget,
            tokenizer=tokenizer,
            tokenizer_revision=tokenizer_revision,
            max_attempts=max_attempts,
            producer=producer,
        )
        for document in documents
        for method in methods
        for budget in budgets
    )
    audit_budget_matrix(
        artifacts,
        document_ids={document.document_id for document in documents},
        methods=methods,
        budgets=budgets,
        tokenizer_revision=tokenizer_revision,
    )
    return artifacts


def audit_budget_matrix(
    artifacts: tuple[BudgetArtifact, ...],
    *,
    document_ids: set[str],
    methods: tuple[str, ...],
    budgets: tuple[int, ...],
    tokenizer_revision: str,
) -> None:
    keys = [item.key for item in artifacts]
    if len(keys) != len(set(keys)):
        raise ValueError("budget matrix contains duplicate combinations")
    expected = {
        (document_id, method, budget)
        for document_id in document_ids
        for method in methods
        for budget in budgets
    }
    if set(keys) != expected:
        raise ValueError("budget matrix has missing or extra combinations")
    if any(item.tokenizer_revision != tokenizer_revision for item in artifacts):
        raise ValueError("budget matrix mixes tokenizer revisions")
    if any(item.valid and item.token_count > item.budget for item in artifacts):
        raise ValueError("valid budget artifact exceeds its budget")


def budget_matrix_digest(artifacts: tuple[BudgetArtifact, ...]) -> str:
    payload = "\n".join(
        f"{item.document_id}|{item.method}|{item.budget}|{item.token_count}|{item.valid}"
        for item in artifacts
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _generate_with_budget(
    document: GeneratedDocument,
    *,
    method: str,
    budget: int,
    tokenizer: TokenCounter,
    tokenizer_revision: str,
    max_attempts: int,
    producer: RepresentationProducer,
) -> BudgetArtifact:
    text = ""
    token_count = 0
    for attempt in range(1, max_attempts + 1):
        text = producer.produce(
            document,
            method=method,
            budget=budget,
            attempt=attempt,
        )
        token_count = tokenizer.count(text)
        if token_count <= budget:
            return BudgetArtifact(
                document_id=document.document_id,
                method=method,
                budget=budget,
                tokenizer_revision=tokenizer_revision,
                text=text,
                token_count=token_count,
                attempts=attempt,
                valid=True,
                error=None,
            )
    return BudgetArtifact(
        document_id=document.document_id,
        method=method,
        budget=budget,
        tokenizer_revision=tokenizer_revision,
        text=text,
        token_count=token_count,
        attempts=max_attempts,
        valid=False,
        error=f"budget_exceeded: {token_count} > {budget}",
    )
