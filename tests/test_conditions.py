from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ism.config import Condition
from ism.data.generator import SyntheticGenerator
from ism.experiments.audit import write_condition_audit
from ism.experiments.conditions import (
    ConditionMatrix,
    audit_condition_matrix,
    build_condition_matrix,
)
from ism.representation.tokenizer import WhitespaceTokenCounter


def matrix(
    conditions: tuple[Condition, ...] = (
        "full_context",
        "full_symbol_dict",
        "symbol_only",
        "corrupted_dict",
        "random_symbol",
        "model_summary",
    ),
) -> ConditionMatrix:
    return build_condition_matrix(
        SyntheticGenerator(42).generate(3),
        conditions=conditions,
        budget=128,
        seed=42,
        tokenizer=WhitespaceTokenCounter(),
    )


def test_p4_con_001_condition_matrix_is_complete() -> None:
    value = matrix()
    questions = {item.question_id for item in value.inputs}
    conditions = {item.condition for item in value.inputs}

    assert len(value.inputs) == len(questions) * len(conditions)
    assert len({item.key for item in value.inputs}) == len(value.inputs)


def test_p4_con_002_conditions_have_identical_question_sets() -> None:
    value = matrix()
    by_condition = {
        condition: {item.question_id for item in value.inputs if item.condition == condition}
        for condition in {item.condition for item in value.inputs}
    }

    assert len({frozenset(question_ids) for question_ids in by_condition.values()}) == 1


def test_p4_con_003_ism_conditions_share_document_source() -> None:
    value = matrix()
    ism_inputs = [item for item in value.inputs if item.method == "ism"]

    by_document: dict[str, set[str | None]] = {}
    for item in ism_inputs:
        by_document.setdefault(item.document_id, set()).add(item.source_compression_id)

    assert all(len(source_ids) == 1 for source_ids in by_document.values())
    assert all(None not in source_ids for source_ids in by_document.values())


def test_p4_cfg_001_duplicate_condition_is_rejected() -> None:
    with pytest.raises(ValueError, match="unique"):
        matrix(("full_context", "full_context"))


def test_p4_fun_001_full_context_bypasses_compression() -> None:
    value = matrix(("full_context",))

    assert value.compressions == ()
    assert all(item.source_compression_id is None for item in value.inputs)


def test_p4_fun_002_model_summary_has_distinct_method_and_compression() -> None:
    value = matrix(("full_symbol_dict", "model_summary"))
    methods = {item.method for item in value.compressions}

    assert methods == {"ism", "model_summary"}
    assert all(
        item.source_compression_id is not None
        for item in value.inputs
        if item.condition == "model_summary"
    )


def test_p4_io_001_audit_count_matches_matrix(tmp_path: Path) -> None:
    value = matrix(("full_context", "full_symbol_dict"))
    path = tmp_path / "condition-audit.json"

    write_condition_audit(path, value)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["input_count"] == len(value.inputs)
    assert payload["compression_count"] == len(value.compressions)
    assert len(payload["records"]) == len(value.inputs)


def test_audit_rejects_missing_condition_record() -> None:
    value = matrix(("full_context", "full_symbol_dict"))
    damaged = ConditionMatrix(
        compressions=value.compressions,
        inputs=value.inputs[:-1],
    )

    with pytest.raises(ValueError, match="mismatch"):
        audit_condition_matrix(
            damaged,
            expected_questions={item.question_id for item in value.inputs},
            conditions=("full_context", "full_symbol_dict"),
        )


def test_p4_reg_001_three_document_golden_input_hashes() -> None:
    value = matrix(("full_context", "full_symbol_dict", "symbol_only"))
    digest = hashlib.sha256(
        "\n".join(item.input_hash for item in value.inputs).encode()
    ).hexdigest()

    assert digest == "87847a88f39f6414c5a490a05298554c45e5907480b9eeff2a445eac2133840c"
