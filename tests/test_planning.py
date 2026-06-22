from __future__ import annotations

from pathlib import Path

import pytest

from ism.config import load_config
from ism.planning import build_execution_plan, estimate_server_requirements

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


def test_cost_cfg_003_and_004_server_estimate_uses_pilot_values() -> None:
    estimate = estimate_server_requirements(
        build_execution_plan(load_config(SMOKE_CONFIG)),
        calls_per_second=0.2,
        bytes_per_call=100_000,
        approved_gpu_hours=1,
    )

    assert estimate.estimated_gpu_hours == 0.0875
    assert estimate.estimated_storage_bytes == 6_300_000


def test_cost_cfg_005_missing_gpu_quota_is_rejected() -> None:
    with pytest.raises(ValueError, match="approved_gpu_hours"):
        estimate_server_requirements(
            build_execution_plan(load_config(SMOKE_CONFIG)),
            calls_per_second=1,
            bytes_per_call=100,
            approved_gpu_hours=0,
        )


def test_cost_cfg_006_estimate_over_quota_is_rejected() -> None:
    with pytest.raises(ValueError, match="exceeds"):
        estimate_server_requirements(
            build_execution_plan(load_config(SMOKE_CONFIG)),
            calls_per_second=0.01,
            bytes_per_call=100,
            approved_gpu_hours=1,
        )
