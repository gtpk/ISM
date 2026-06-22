from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SMOKE_CONFIG = ROOT / "configs/experiments/smoke.yaml"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "ism", *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_p0_reg_001_help_succeeds() -> None:
    result = run_cli("--help")

    assert result.returncode == 0
    assert "validate-config" in result.stdout
    assert "dry-run" in result.stdout
    assert "generate-synthetic" in result.stdout
    assert "run-mock" in result.stdout
    assert "audit-conditions" in result.stdout
    assert "audit-budgets" in result.stdout
    assert "report-run" in result.stdout
    assert "estimate-server" in result.stdout


def test_p0_reg_001_validate_config_succeeds() -> None:
    result = run_cli("validate-config", "--config", str(SMOKE_CONFIG))

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    # validate-config prints the canonical config identity (what config_hash
    # covers): deployment-independent POSIX relative paths, so local and Colab
    # see byte-identical output. See COL-ENV-004 / docs/decisions.
    assert payload["dataset"]["path"] == "data/processed/synthetic-v1"
    assert payload["output"]["artifact_dir"] == "artifacts"


def test_p0_reg_001_dry_run_succeeds() -> None:
    result = run_cli("dry-run", "--config", str(SMOKE_CONFIG))

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["plan"]["compression_calls"] == 3
    assert payload["plan"]["reasoning_calls"] == 18
    assert payload["plan"]["nominal_calls"] == 21
    assert payload["plan"]["worst_case_calls"] == 63


def test_p0_err_001_invalid_arguments_fail() -> None:
    result = run_cli("not-a-command")

    assert result.returncode != 0
    assert "invalid choice" in result.stderr


def test_p1_cli_001_generate_synthetic(tmp_path: Path) -> None:
    output = tmp_path / "synthetic.jsonl"

    result = run_cli(
        "generate-synthetic",
        "--config",
        str(SMOKE_CONFIG),
        "--output",
        str(output),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["documents"] == 3
    assert payload["questions"] == 6
    assert output.exists()
    assert len(output.read_text(encoding="utf-8").splitlines()) == 3


def test_p3_int_001_run_mock_end_to_end(tmp_path: Path) -> None:
    output = tmp_path / "mock-run"

    result = run_cli(
        "run-mock",
        "--config",
        str(SMOKE_CONFIG),
        "--output",
        str(output),
        "--batch-size",
        "4",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["documents"] == 3
    assert payload["questions"] == 6
    assert payload["predictions"] == 18
    assert payload["accuracy"] == 1
    assert (output / "predictions.jsonl").exists()
    assert (output / "metrics.json").exists()
    assert (output / "manifest.json").exists()


def test_p4_cli_001_condition_audit(tmp_path: Path) -> None:
    output = tmp_path / "condition-audit.json"

    result = run_cli(
        "audit-conditions",
        "--config",
        str(SMOKE_CONFIG),
        "--output",
        str(output),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["inputs"] == 18
    assert payload["compressions"] == 3
    assert output.exists()


def test_p5_cli_001_budget_audit(tmp_path: Path) -> None:
    output = tmp_path / "budget-audit.json"

    result = run_cli(
        "audit-budgets",
        "--config",
        str(SMOKE_CONFIG),
        "--output",
        str(output),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["artifacts"] == 3
    assert payload["invalid"] == 0
    assert output.exists()


def test_p9_cli_001_report_from_local_artifacts(tmp_path: Path) -> None:
    run_dir = tmp_path / "mock-run"
    audit_path = tmp_path / "condition-audit.json"
    report_dir = tmp_path / "report"
    assert (
        run_cli(
            "run-mock",
            "--config",
            str(SMOKE_CONFIG),
            "--output",
            str(run_dir),
        ).returncode
        == 0
    )
    assert (
        run_cli(
            "audit-conditions",
            "--config",
            str(SMOKE_CONFIG),
            "--output",
            str(audit_path),
        ).returncode
        == 0
    )

    result = run_cli(
        "report-run",
        "--config",
        str(SMOKE_CONFIG),
        "--predictions",
        str(run_dir / "predictions.jsonl"),
        "--condition-audit",
        str(audit_path),
        "--output",
        str(report_dir),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["conditions"] == 3
    assert (report_dir / "metrics.json").exists()
    assert (report_dir / "metrics.csv").exists()
    assert (report_dir / "metrics.md").exists()


def test_cost_cli_001_server_estimate() -> None:
    result = run_cli(
        "estimate-server",
        "--config",
        str(SMOKE_CONFIG),
        "--calls-per-second",
        "0.2",
        "--bytes-per-call",
        "100000",
        "--approved-gpu-hours",
        "1",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["estimated_gpu_hours"] == 0.0875
    assert payload["estimated_storage_bytes"] == 6_300_000
