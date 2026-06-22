from __future__ import annotations

import hashlib
import math
from pathlib import Path

import pytest

from ism.config import load_config
from ism.evaluation.audit import EvaluationPrediction, audit_predictions
from ism.evaluation.manifest import FrozenRunManifest, RunProvenance
from ism.evaluation.metrics import (
    calculate_condition_metric,
    swap_robustness,
)
from ism.evaluation.reporting import build_report_rows, write_report
from ism.evaluation.statistics import (
    holm_correction,
    mcnemar_exact,
    paired_bootstrap_difference,
)

ROOT = Path(__file__).resolve().parents[1]
SMOKE_CONFIG = ROOT / "configs/experiments/smoke.yaml"


def metric():
    return calculate_condition_metric(
        condition="full_symbol_dict",
        correct=(True, True, False, False),
        full_correct=(True, True, True, False),
        compressed_tokens=250,
        full_tokens=1000,
    )


def test_p9_cfg_001_frozen_config_detects_change() -> None:
    config = load_config(SMOKE_CONFIG)
    manifest = FrozenRunManifest.create(
        run_id="run",
        config=config,
        provenance=RunProvenance(
            git_commit="abc123",
            model_revision="model-rev",
            tokenizer_revision="tokenizer-rev",
            seed=42,
        ),
    )
    changed = config.model_copy(
        update={
            "compression": config.compression.model_copy(
                update={"budget": config.compression.budget + 1}
            )
        }
    )

    manifest.verify_config(config)
    with pytest.raises(ValueError, match="changed"):
        manifest.verify_config(changed)


def test_p9_cfg_002_provenance_requires_all_fields() -> None:
    config = load_config(SMOKE_CONFIG)

    with pytest.raises(ValueError, match="must not be empty"):
        FrozenRunManifest.create(
            run_id="run",
            config=config,
            provenance=RunProvenance(
                git_commit="",
                model_revision="model-rev",
                tokenizer_revision="tokenizer-rev",
                seed=42,
            ),
        )


def test_p9_con_001_prediction_keys_are_unique() -> None:
    prediction = EvaluationPrediction(
        run_id="run",
        question_id="q1",
        condition="full",
        correct=True,
    )

    with pytest.raises(ValueError, match="unique"):
        audit_predictions((prediction, prediction), conditions=("full",))


def test_p9_con_002_paired_conditions_require_equal_sample_sets() -> None:
    predictions = (
        EvaluationPrediction("run", "q1", "full", True),
        EvaluationPrediction("run", "q2", "full", True),
        EvaluationPrediction("run", "q1", "ism", True),
    )

    with pytest.raises(ValueError, match="identical"):
        audit_predictions(predictions, conditions=("full", "ism"))


def test_p9_fun_001_metric_fixture_matches_manual_values() -> None:
    value = metric()

    assert value.accuracy == 0.5
    assert value.accuracy_retention is not None
    assert math.isclose(value.accuracy_retention, 2 / 3)
    assert value.compression_ratio == 0.25
    assert value.efficiency_score is not None
    assert math.isclose(value.efficiency_score, 8 / 3)
    robustness = swap_robustness(unseen_accuracy=0.6, original_accuracy=0.75)
    assert robustness is not None
    assert math.isclose(robustness, 0.8)


def test_p9_fun_002_zero_denominators_are_explicitly_undefined() -> None:
    value = calculate_condition_metric(
        condition="ism",
        correct=(False,),
        full_correct=(False,),
        compressed_tokens=0,
        full_tokens=100,
    )

    assert value.accuracy_retention is None
    assert value.compression_ratio == 0
    assert value.efficiency_score is None
    assert swap_robustness(unseen_accuracy=0, original_accuracy=0) is None


def test_p9_fun_003_bootstrap_is_seed_deterministic() -> None:
    first = paired_bootstrap_difference(
        (1, 1, 0, 1),
        (1, 0, 0, 0),
        seed=42,
        iterations=1000,
    )
    second = paired_bootstrap_difference(
        (1, 1, 0, 1),
        (1, 0, 0, 0),
        seed=42,
        iterations=1000,
    )

    assert first == second
    assert first.estimate == 0.5
    assert first.lower <= first.estimate <= first.upper


def test_p9_fun_004_mcnemar_exact_fixture() -> None:
    first_only, second_only, p_value = mcnemar_exact(
        (True, False, False, False),
        (False, True, True, True),
    )

    assert (first_only, second_only) == (1, 3)
    assert p_value == 0.625


def test_p9_fun_005_holm_correction_fixture() -> None:
    actual = holm_correction((0.01, 0.04, 0.03))

    assert all(
        math.isclose(value, expected)
        for value, expected in zip(actual, (0.03, 0.06, 0.06), strict=True)
    )


def test_p9_io_001_report_rows_include_source_and_metric_key() -> None:
    rows = build_report_rows(run_id="run-1", metrics=(metric(),))

    assert len(rows) == 4
    assert all(row.source_run_id == "run-1" for row in rows)
    assert {row.metric_key for row in rows} == {
        "accuracy",
        "accuracy_retention",
        "compression_ratio",
        "efficiency_score",
    }


def test_p9_io_002_rerender_does_not_modify_raw_artifact(tmp_path: Path) -> None:
    raw = tmp_path / "raw.jsonl"
    raw.write_text('{"prediction": "HIGH"}\n', encoding="utf-8")
    before = raw.read_bytes()
    rows = build_report_rows(run_id="run-1", metrics=(metric(),))

    write_report(tmp_path / "report", rows)
    write_report(tmp_path / "report", rows)

    assert raw.read_bytes() == before


def test_p9_reg_001_golden_report_files(tmp_path: Path) -> None:
    output = tmp_path / "report"
    write_report(output, build_report_rows(run_id="run-1", metrics=(metric(),)))
    payload = b"".join(
        (output / name).read_bytes() for name in ("metrics.json", "metrics.csv", "metrics.md")
    )

    assert hashlib.sha256(payload).hexdigest() == (
        "7e217997026cf718cba321c44f570640f0b4ff4e262601dec990b089baac38e5"
    )
