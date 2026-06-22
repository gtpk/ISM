from __future__ import annotations

from pathlib import Path

from ism.config import load_config
from ism.planning import build_execution_plan

ROOT = Path(__file__).resolve().parents[1]
SMOKE_CONFIG = ROOT / "configs/experiments/smoke.yaml"


def test_ism_derived_conditions_share_one_document_compression() -> None:
    config = load_config(SMOKE_CONFIG)

    plan = build_execution_plan(config)

    assert plan.documents == 3
    assert plan.compression_calls == 3
    assert plan.reasoning_calls == 18


def test_model_summary_adds_a_distinct_compression_family() -> None:
    config = load_config(SMOKE_CONFIG)
    updated = config.model_copy(update={"conditions": [*config.conditions, "model_summary"]})

    plan = build_execution_plan(updated)

    assert plan.compression_calls == 6
