from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

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
