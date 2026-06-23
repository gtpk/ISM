from __future__ import annotations

import json
from pathlib import Path

from ism.config import load_config
from ism.data.generator import SyntheticGenerator
from ism.experiments.fixed_budget import merge_fixed_budget, run_fixed_budget_experiment
from ism.experiments.methods import (
    compute_idf,
    keyword_extract_text,
    oracle_gold_summary_text,
)
from ism.inference.contracts import GenerationRequest, GenerationResult
from ism.inference.mock import MockTextGenerator
from ism.representation.tokenizer import WhitespaceTokenCounter

ROOT = Path(__file__).resolve().parents[1]
MOCK_CONFIG = ROOT / "configs/experiments/ablation_mock.yaml"
LLM_CONFIG = ROOT / "configs/experiments/ablation_qwen7b.yaml"

_VALID_ISM = (
    "[DICTIONARY]\n"
    "Z1 := IF condition a THEN risk = HIGH\n"
    "Z2 := IF condition b THEN review = true\n\n"
    "[RELATIONS]\nZ1 Z2\n"
)


class _FakeLlmGenerator:
    def generate(self, requests: tuple[GenerationRequest, ...]) -> tuple[GenerationResult, ...]:
        results: list[GenerationResult] = []
        for request in requests:
            if ":compress:" in request.request_id:
                text: str | None = _VALID_ISM
            elif ":summary:" in request.request_id:
                text = "short summary within budget"
            else:
                text = request.expected_output
            results.append(
                GenerationResult(
                    request_id=request.request_id, text=text or "", input_tokens=1, output_tokens=1
                )
            )
        return tuple(results)


def _docs(n: int = 4):
    return SyntheticGenerator(42).generate(n, split="dev")


def test_keyword_extract_respects_budget() -> None:
    docs = _docs(4)
    idf = compute_idf(docs)
    tok = WhitespaceTokenCounter()
    for budget in (8, 16, 32):
        text = keyword_extract_text(docs[0], budget=budget, idf=idf)
        assert tok.count(text) <= budget


def test_oracle_gold_summary_respects_budget() -> None:
    docs = _docs(4)
    tok = WhitespaceTokenCounter()
    for budget in (16, 32, 64):
        text = oracle_gold_summary_text(docs[0], budget=budget)
        assert tok.count(text) <= budget


def test_fixed_budget_smoke_deterministic_methods(tmp_path: Path) -> None:
    config = load_config(MOCK_CONFIG)
    summary = run_fixed_budget_experiment(
        config,
        output_dir=tmp_path,
        generator=MockTextGenerator(),
        budgets=(16, 32),
        methods=("full_context", "keyword_extract", "oracle_gold_summary", "model_summary"),
    )
    cells = {(r.method, r.budget) for r in summary.results}
    assert ("full_context", 0) in cells
    assert ("keyword_extract", 16) in cells and ("keyword_extract", 32) in cells
    full = next(r for r in summary.results if r.method == "full_context")
    assert full.compression_ratio == 1.0
    assert full.accuracy_retention == 1.0
    # Compressed methods are shorter than full context.
    kw = next(r for r in summary.results if r.method == "keyword_extract" and r.budget == 16)
    assert kw.compression_ratio is not None and kw.compression_ratio < 1.0
    assert (tmp_path / "fixed_budget_summary.json").is_file()


def test_fixed_budget_includes_ism_with_llm_generator(tmp_path: Path) -> None:
    config = load_config(LLM_CONFIG)
    summary = run_fixed_budget_experiment(
        config,
        output_dir=tmp_path,
        generator=_FakeLlmGenerator(),
        budgets=(64,),
        methods=("full_context", "ism", "model_summary"),
        doc_count=3,
    )
    methods = {r.method for r in summary.results}
    assert {"full_context", "ism", "model_summary"} <= methods
    payload = json.loads((tmp_path / "fixed_budget_summary.json").read_text())
    assert payload["budgets"] == [64]
    # Paired summary-vs-ism contrast is reported per budget where both exist.
    names = {(c.name, c.budget) for c in summary.paired_contrasts}
    assert ("summary_vs_ism", 64) in names


def test_merge_fixed_budget_combines_shards(tmp_path: Path) -> None:
    config = load_config(MOCK_CONFIG)
    methods = ("full_context", "keyword_extract", "model_summary")
    shard_a = tmp_path / "a"
    shard_b = tmp_path / "b"
    run_fixed_budget_experiment(
        config, output_dir=shard_a, generator=MockTextGenerator(),
        budgets=(32,), methods=methods, doc_offset=0, doc_count=2,
    )
    run_fixed_budget_experiment(
        config, output_dir=shard_b, generator=MockTextGenerator(),
        budgets=(32,), methods=methods, doc_offset=2, doc_count=2,
    )
    merged = merge_fixed_budget(
        (shard_a, shard_b), output_dir=tmp_path / "merged", run_id="merged", seed=42
    )
    assert merged.documents == 4
    # 4 docs x 2 questions x (full_context + 2 methods @ 1 budget) = 24
    assert merged.predictions == 24
    assert (tmp_path / "merged" / "fixed_budget_summary.json").is_file()
