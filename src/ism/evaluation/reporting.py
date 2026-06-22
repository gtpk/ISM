from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

from ism.evaluation.metrics import ConditionMetric, calculate_condition_metric


@dataclass(frozen=True)
class ReportRow:
    source_run_id: str
    metric_key: str
    condition: str
    value: float | None


def build_report_rows(
    *,
    run_id: str,
    metrics: tuple[ConditionMetric, ...],
) -> tuple[ReportRow, ...]:
    rows: list[ReportRow] = []
    for metric in metrics:
        for key, value in (
            ("accuracy", metric.accuracy),
            ("accuracy_retention", metric.accuracy_retention),
            ("compression_ratio", metric.compression_ratio),
            ("efficiency_score", metric.efficiency_score),
        ):
            rows.append(
                ReportRow(
                    source_run_id=run_id,
                    metric_key=key,
                    condition=metric.condition,
                    value=value,
                )
            )
    return tuple(rows)


def write_report(output_dir: Path, rows: tuple[ReportRow, ...]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "metrics.json"
    csv_path = output_dir / "metrics.csv"
    markdown_path = output_dir / "metrics.md"

    json_path.write_text(
        json.dumps([asdict(row) for row in rows], ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=["source_run_id", "metric_key", "condition", "value"],
        )
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)
    lines = [
        "| Source Run | Metric | Condition | Value |",
        "|---|---|---|---:|",
        *(
            f"| {row.source_run_id} | {row.metric_key} | {row.condition} | "
            f"{'undefined' if row.value is None else f'{row.value:.6f}'} |"
            for row in rows
        ),
    ]
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def report_from_artifacts(
    *,
    predictions_path: Path,
    condition_audit_path: Path,
    output_dir: Path,
    run_id: str,
) -> tuple[ConditionMetric, ...]:
    predictions = _read_jsonl(predictions_path)
    audit_raw: Any = json.loads(condition_audit_path.read_text(encoding="utf-8"))
    if not isinstance(audit_raw, dict):
        raise ValueError("condition audit must be an object")
    audit = cast(dict[str, Any], audit_raw)
    raw_records = audit.get("records")
    if not isinstance(raw_records, list):
        raise ValueError("condition audit records must be a list")
    raw_record_list = cast(list[Any], raw_records)
    audit_records = [
        cast(dict[str, Any], item) for item in raw_record_list if isinstance(item, dict)
    ]
    if len(audit_records) != len(raw_record_list):
        raise ValueError("condition audit record must be an object")

    correct_by_condition: dict[str, dict[str, bool]] = {}
    for item in predictions:
        condition = _required_string(item, "condition")
        question_id = _required_string(item, "question_id")
        correct = item.get("correct")
        if not isinstance(correct, bool):
            raise ValueError("prediction correct must be boolean")
        bucket = correct_by_condition.setdefault(condition, {})
        if question_id in bucket:
            raise ValueError("duplicate prediction question-condition")
        bucket[question_id] = correct
    if "full_context" not in correct_by_condition:
        raise ValueError("full_context predictions are required")
    question_ids = tuple(sorted(correct_by_condition["full_context"]))
    if any(set(values) != set(question_ids) for values in correct_by_condition.values()):
        raise ValueError("prediction conditions have different question sets")

    tokens_by_condition: dict[str, dict[str, int]] = {}
    for item in audit_records:
        condition = _required_string(item, "condition")
        document_id = _required_string(item, "document_id")
        token_count = item.get("token_count")
        if not isinstance(token_count, int):
            raise ValueError("condition token_count must be integer")
        existing = tokens_by_condition.setdefault(condition, {}).get(document_id)
        if existing is not None and existing != token_count:
            raise ValueError("document-condition token count is inconsistent")
        tokens_by_condition[condition][document_id] = token_count
    full_tokens = sum(tokens_by_condition["full_context"].values())
    full_correct = tuple(
        correct_by_condition["full_context"][question_id] for question_id in question_ids
    )
    metrics = tuple(
        calculate_condition_metric(
            condition=condition,
            correct=tuple(values[question_id] for question_id in question_ids),
            full_correct=full_correct,
            compressed_tokens=sum(tokens_by_condition[condition].values()),
            full_tokens=full_tokens,
        )
        for condition, values in sorted(correct_by_condition.items())
    )
    write_report(output_dir, build_report_rows(run_id=run_id, metrics=metrics))
    return metrics


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        try:
            raw: Any = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"{path}:{line_number}: invalid JSON") from error
        if not isinstance(raw, dict):
            raise ValueError(f"{path}:{line_number}: record must be an object")
        records.append(cast(dict[str, Any], raw))
    return records


def _required_string(value: dict[str, Any], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item:
        raise ValueError(f"{key} must be a non-empty string")
    return item
