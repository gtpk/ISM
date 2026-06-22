from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest
import yaml
from pydantic import ValidationError

from ism.config import AppConfig, load_config

ROOT = Path(__file__).resolve().parents[1]
SMOKE_CONFIG = ROOT / "configs/experiments/smoke.yaml"


def load_raw() -> dict[str, object]:
    value = yaml.safe_load(SMOKE_CONFIG.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def test_p0_con_001_minimum_config_loads_as_typed_model() -> None:
    config = load_config(SMOKE_CONFIG)

    assert isinstance(config, AppConfig)
    assert config.dataset.max_documents == 3
    assert config.execution_budget.stage.value == "L2"


def test_p0_cfg_001_unknown_key_reports_field_path() -> None:
    raw = load_raw()
    raw["unknown_section"] = {"enabled": True}

    with pytest.raises(ValidationError) as captured:
        AppConfig.model_validate(raw)

    assert "unknown_section" in str(captured.value)
    assert "Extra inputs are not permitted" in str(captured.value)


def test_p0_cfg_002_cpu_and_four_bit_conflict_is_rejected() -> None:
    raw = load_raw()
    model = raw["model"]
    assert isinstance(model, dict)
    model["load_in_4bit"] = True

    with pytest.raises(ValidationError, match="load_in_4bit"):
        AppConfig.model_validate(raw)


def test_p0_cfg_002_local_stage_with_gpu_hours_is_rejected() -> None:
    raw = load_raw()
    budget = raw["execution_budget"]
    assert isinstance(budget, dict)
    budget["max_gpu_hours"] = 1

    with pytest.raises(ValidationError, match="local stages"):
        AppConfig.model_validate(raw)


def test_p0_io_001_relative_paths_resolve_from_project_root(
    tmp_path: Path,
) -> None:
    nested = ROOT / "configs/experiments"
    copied = tmp_path / "copied.yaml"
    copied.write_text(SMOKE_CONFIG.read_text(encoding="utf-8"), encoding="utf-8")

    from_original = load_config(nested / "smoke.yaml")
    from_copy = load_config(copied, project_root=ROOT)

    assert from_original.dataset.path == from_copy.dataset.path
    assert from_original.output.artifact_dir == from_copy.output.artifact_dir


def test_p0_det_001_resolved_serialization_is_byte_identical() -> None:
    first = load_config(SMOKE_CONFIG)
    second = load_config(SMOKE_CONFIG)

    assert first.stable_json().encode() == second.stable_json().encode()
    assert first.config_hash() == second.config_hash()


def test_col_env_004_config_hash_is_project_root_independent(tmp_path: Path) -> None:
    copied = tmp_path / "smoke.yaml"
    copied.write_text(SMOKE_CONFIG.read_text(encoding="utf-8"), encoding="utf-8")

    here = load_config(SMOKE_CONFIG)
    there = load_config(copied, project_root=tmp_path)

    # Runtime paths differ per deployment ...
    assert here.dataset.path != there.dataset.path
    assert here.output.artifact_dir != there.output.artifact_dir
    # ... but the serialized identity and hash must match across roots
    # (local <-> Colab). The identity uses POSIX relative paths only.
    assert here.stable_json() == there.stable_json()
    assert here.config_hash() == there.config_hash()
    assert "data/processed/synthetic-v1" in here.stable_json()
