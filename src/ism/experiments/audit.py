from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path

from ism.experiments.budgets import BudgetArtifact
from ism.experiments.conditions import ConditionMatrix


def write_condition_audit(path: Path, matrix: ConditionMatrix) -> None:
    payload = {
        "compression_count": len(matrix.compressions),
        "input_count": len(matrix.inputs),
        "conditions": sorted({item.condition for item in matrix.inputs}),
        "question_count": len({item.question_id for item in matrix.inputs}),
        "records": [
            {
                "question_id": item.question_id,
                "document_id": item.document_id,
                "condition": item.condition,
                "input_hash": item.input_hash,
                "source_compression_id": item.source_compression_id,
                "method": item.method,
                "token_count": item.token_count,
            }
            for item in matrix.inputs
        ],
    }
    _write_json_atomic(path, payload)


def write_budget_audit(path: Path, artifacts: tuple[BudgetArtifact, ...]) -> None:
    payload = {
        "artifact_count": len(artifacts),
        "invalid_count": sum(not item.valid for item in artifacts),
        "methods": sorted({item.method for item in artifacts}),
        "budgets": sorted({item.budget for item in artifacts}),
        "tokenizer_revisions": sorted({item.tokenizer_revision for item in artifacts}),
        "records": [
            {
                "document_id": item.document_id,
                "method": item.method,
                "budget": item.budget,
                "tokenizer_revision": item.tokenizer_revision,
                "token_count": item.token_count,
                "attempts": item.attempts,
                "valid": item.valid,
                "error": item.error,
            }
            for item in artifacts
        ],
    }
    _write_json_atomic(path, payload)


def _write_json_atomic(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        text=True,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary_path.replace(path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise
