from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass

from ism.config import Condition
from ism.data.generator import GeneratedDocument
from ism.data.render import render_rule
from ism.representation.interventions import (
    corrupt_dictionary,
    random_symbol_control,
    remove_dictionary,
)
from ism.representation.models import ISMRepresentation, SymbolDefinition
from ism.representation.parser import serialize_ism
from ism.representation.tokenizer import TokenCounter


@dataclass(frozen=True)
class CompressionRecord:
    compression_id: str
    document_id: str
    method: str
    budget: int
    representation: ISMRepresentation | None
    serialized_text: str
    token_count: int


@dataclass(frozen=True)
class ConditionInput:
    question_id: str
    document_id: str
    condition: str
    input_text: str
    input_hash: str
    source_compression_id: str | None
    method: str
    token_count: int

    @property
    def key(self) -> tuple[str, str]:
        return (self.question_id, self.condition)


@dataclass(frozen=True)
class ConditionMatrix:
    compressions: tuple[CompressionRecord, ...]
    inputs: tuple[ConditionInput, ...]


def build_condition_matrix(
    documents: tuple[GeneratedDocument, ...],
    *,
    conditions: tuple[Condition, ...],
    budget: int,
    seed: int,
    tokenizer: TokenCounter,
    ism_representation: Callable[[GeneratedDocument], ISMRepresentation] | None = None,
) -> ConditionMatrix:
    """Build per-condition inputs for every (document, question).

    ``ism_representation`` supplies the ISM for a document; when omitted the ISM
    is derived deterministically from the gold rule graph (oracle). The paper's
    main setup injects an LLM compressor here instead.
    """
    if len(conditions) != len(set(conditions)):
        raise ValueError("conditions must be unique")
    compressions: list[CompressionRecord] = []
    inputs: list[ConditionInput] = []

    for document in documents:
        ism = _build_ism_compression(
            document,
            budget=budget,
            tokenizer=tokenizer,
            representation=None if ism_representation is None else ism_representation(document),
        )
        required_methods = {_method_for_condition(condition) for condition in conditions}
        method_records: dict[str, CompressionRecord] = {}
        if "ism" in required_methods:
            method_records["ism"] = ism
            compressions.append(ism)
        for method in sorted(required_methods - {"full_context", "ism"}):
            record = _build_text_compression(
                document,
                method=method,
                budget=budget,
                tokenizer=tokenizer,
            )
            method_records[method] = record
            compressions.append(record)

        for question in document.questions:
            for condition in conditions:
                method = _method_for_condition(condition)
                text, source_id = _condition_text(
                    document,
                    condition=condition,
                    ism=ism,
                    method_records=method_records,
                    seed=seed,
                    tokenizer=tokenizer,
                )
                inputs.append(
                    ConditionInput(
                        question_id=question.question_id,
                        document_id=document.document_id,
                        condition=condition,
                        input_text=text,
                        input_hash=hashlib.sha256(text.encode()).hexdigest(),
                        source_compression_id=source_id,
                        method=method,
                        token_count=tokenizer.count(text),
                    )
                )
    matrix = ConditionMatrix(compressions=tuple(compressions), inputs=tuple(inputs))
    audit_condition_matrix(
        matrix,
        expected_questions={
            question.question_id for document in documents for question in document.questions
        },
        conditions=conditions,
    )
    return matrix


def audit_condition_matrix(
    matrix: ConditionMatrix,
    *,
    expected_questions: set[str],
    conditions: tuple[Condition, ...],
) -> None:
    keys = [item.key for item in matrix.inputs]
    if len(keys) != len(set(keys)):
        raise ValueError("condition matrix contains duplicate question-condition records")
    expected = {
        (question_id, condition) for question_id in expected_questions for condition in conditions
    }
    missing = expected - set(keys)
    extra = set(keys) - expected
    if missing or extra:
        raise ValueError(
            f"condition matrix mismatch: missing={sorted(missing)}, extra={sorted(extra)}"
        )

    ism_ids_by_document = {
        item.document_id: item.compression_id
        for item in matrix.compressions
        if item.method == "ism"
    }
    for item in matrix.inputs:
        if item.condition == "full_context":
            if item.source_compression_id is not None:
                raise ValueError("full_context must not reference a compression")
        elif item.method == "ism":
            expected_id = ism_ids_by_document.get(item.document_id)
            if item.source_compression_id != expected_id:
                raise ValueError("ISM condition does not reference its document compression")


def _build_ism_compression(
    document: GeneratedDocument,
    *,
    budget: int,
    tokenizer: TokenCounter,
    representation: ISMRepresentation | None = None,
) -> CompressionRecord:
    if representation is None:
        definitions = tuple(
            SymbolDefinition(label=f"Z{index}", definition=render_rule(rule))
            for index, rule in enumerate(document.graph.rules, start=1)
        )
        labels = tuple(item.label for item in definitions)
        representation = ISMRepresentation(
            symbols=labels,
            dictionary=definitions,
            relations=(" ".join(labels),),
        )
    serialized = serialize_ism(representation)
    return _compression_record(
        document,
        method="ism",
        budget=budget,
        representation=representation,
        text=serialized,
        tokenizer=tokenizer,
    )


def _build_text_compression(
    document: GeneratedDocument,
    *,
    method: str,
    budget: int,
    tokenizer: TokenCounter,
) -> CompressionRecord:
    words = document.document_text.split()
    text = " ".join(words[:budget])
    return _compression_record(
        document,
        method=method,
        budget=budget,
        representation=None,
        text=text,
        tokenizer=tokenizer,
    )


def _compression_record(
    document: GeneratedDocument,
    *,
    method: str,
    budget: int,
    representation: ISMRepresentation | None,
    text: str,
    tokenizer: TokenCounter,
) -> CompressionRecord:
    identity = "\x1f".join((document.document_id, method, str(budget), text))
    return CompressionRecord(
        compression_id=hashlib.sha256(identity.encode()).hexdigest(),
        document_id=document.document_id,
        method=method,
        budget=budget,
        representation=representation,
        serialized_text=text,
        token_count=tokenizer.count(text),
    )


def _condition_text(
    document: GeneratedDocument,
    *,
    condition: Condition,
    ism: CompressionRecord,
    method_records: dict[str, CompressionRecord],
    seed: int,
    tokenizer: TokenCounter,
) -> tuple[str, str | None]:
    if condition == "full_context":
        return document.document_text, None
    if condition == "full_symbol_dict":
        return ism.serialized_text, ism.compression_id
    if ism.representation is None:
        raise AssertionError("ISM compression must include a representation")
    if condition in {"symbol_only", "unseen_swap_no_dict"}:
        value = remove_dictionary(ism.representation).representation
        return serialize_ism(value), ism.compression_id
    if condition == "corrupted_dict":
        value = corrupt_dictionary(ism.representation, seed=seed).representation
        return serialize_ism(value), ism.compression_id
    if condition == "random_symbol":
        value = random_symbol_control(
            ism.representation,
            seed=seed,
            tokenizer=tokenizer,
            tolerance=1,
        ).representation
        return serialize_ism(value), ism.compression_id
    if condition == "unseen_swap_dict":
        return ism.serialized_text, ism.compression_id
    method = _method_for_condition(condition)
    record = method_records[method]
    return record.serialized_text, record.compression_id


def _method_for_condition(condition: Condition) -> str:
    if condition == "full_context":
        return "full_context"
    if condition in {
        "full_symbol_dict",
        "symbol_only",
        "corrupted_dict",
        "random_symbol",
        "unseen_swap_dict",
        "unseen_swap_no_dict",
    }:
        return "ism"
    return condition
