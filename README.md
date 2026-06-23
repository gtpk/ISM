# Inspectable Symbolic Compression (ISM)

A study of **Inspectable Symbolic Compression** for long-context LLM reasoning:
compressing a long document into reusable discrete text symbols (`Z1`, `Z2`, …)
plus a short dictionary, instead of selecting source tokens or compressing into
continuous vectors. Because the representation is ordinary tokens with an explicit
symbol→meaning map, you can remove the dictionary, corrupt its mappings, or swap
labels and measure the effect on downstream reasoning.

This repository contains the full experiment framework (`src/ism/`, CLI `ism`),
the reproducible run evidence (`docs/evidence/`), and the paper.

## Paper

**Inspectable Symbolic Compression for Long-Context Reasoning: A Mixed-Results
Study Against Natural-Language Summaries** — Taehyuk Kwon (NeurIPS 2026 format).

- 📄 **[View on GitHub](paper/ism-mixed-results.pdf)** ·
  **[Download PDF](https://github.com/gtpk/SESC/raw/main/paper/ism-mixed-results.pdf)**
- LaTeX source: [paper/ism-mixed-results.tex](paper/ism-mixed-results.tex)
  (compile with `tectonic paper/ism-mixed-results.tex`)

### Findings (honest, mixed results)

| RQ | Question | Result |
|---|---|---|
| RQ1 | Is ISM's internal structure actually used by the reasoner? | **Yes** (dev scale): inverting dictionary conclusions and removing symbolic structure each significantly lower accuracy; permuting arbitrary labels does not. |
| RQ3 | At a matched token budget, is ISM more efficient than a same-model summary? | **No**: a natural-language summary is both more accurate and cheaper (McNemar *p* < 0.01 at every budget). |
| RQ4 | Does ISM win on the reuse cost–accuracy frontier? | **No**: the summary dominates ISM on both cost and accuracy. |

We do **not** claim ISM as a better compressor. The contribution is to delimit
where prompt-only symbolic compression fails, and to argue its remaining promise
is as a *programmatically executable semantic IR* handled by a
parser/checker/executor outside the LLM (paper Appendix B). Reproducible run
evidence (artifacts, hashes, environment, commands) is under
[docs/evidence/](docs/evidence/README.md).

## Repository layout

```
src/ism/            Python package and the `ism` CLI
  config.py           experiment config schema + deployment-independent config_hash
  data/               synthetic Rule-QA generator and QASPER adapter
  representation/     ISM format, parser, intervention operators
  inference/          backends (mock CPU / transformers GPU) + run pipeline
  experiments/        ablation, fixed-budget, reuse orchestration
  evaluation/         metrics, scoring, paired statistics, reporting
  training/           LoRA label-swap contract (RQ2, not yet run)
configs/experiments/  YAML configs (smoke, ablation, fixed-budget, s1, …)
docs/                 phase reports, ADRs, reviews, and reproducible evidence
paper/                NeurIPS 2026 paper (.tex/.pdf) and style file
tests/                test suite (run with pytest)
```

## Environment setup

Requirements: **Python 3.11–3.14** and [**uv**](https://docs.astral.sh/uv/) for
dependency management. The core package runs CPU-only; the real-model GPU backend
is an optional extra (see below).

```bash
# Install uv (macOS/Linux), then sync the project + dev dependencies:
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync --dev

# Smoke-test the install:
uv run ism validate-config --config configs/experiments/smoke.yaml
uv run ism dry-run        --config configs/experiments/smoke.yaml
uv run pytest
```

The local repository is the source of truth. Colab/GPU is used only after the
local blocking tests pass.

## Usage

The `ism` CLI is config-driven; every command takes `--config <yaml>`. Run
`uv run ism --help` (or `<command> --help`) for full options.

```bash
# Inspect what a config will do (no model calls):
uv run ism validate-config --config configs/experiments/ablation_qwen7b.yaml
uv run ism dry-run         --config configs/experiments/ablation_qwen7b.yaml   # bounded execution plan
uv run ism estimate-server --config configs/experiments/ablation_qwen7b.yaml   # worst-case GPU time / storage

# Generate data and run locally with the mock (CPU) backend:
uv run ism generate-synthetic --config configs/experiments/smoke.yaml
uv run ism run-mock           --config configs/experiments/smoke.yaml

# Diagnostics:
uv run ism compress-audit --config configs/experiments/ablation_qwen7b.yaml    # ISM structure (purity, self-containment)
uv run ism report-run     --config configs/experiments/ablation_qwen7b.yaml    # render metrics from artifacts
```

| Command | Purpose |
|---|---|
| `validate-config` | Validate and print a resolved experiment config |
| `dry-run` | Print the bounded execution plan |
| `estimate-server` | Estimate worst-case GPU time and storage before a server run |
| `generate-synthetic` | Generate a bounded synthetic dataset from a config |
| `run-mock` | Run the local CPU pipeline with the mock adapter |
| `run` | Run the pipeline with the backend selected in the config |
| `run-ablation` / `merge-ablation` | Experiment 6.1 (Dictionary Ablation, RQ1) + shard merge |
| `run-fixed-budget` / `merge-fixed-budget` | Experiment 6.3 (Fixed-Budget, RQ3) + shard merge |
| `run-reuse` | Experiment 6.4 (Reuse cost/accuracy, RQ4; analytic) |
| `compress-audit` | Compress only and report ISM structure diagnostics |
| `audit-conditions` / `audit-budgets` | Build and validate the condition / method-budget matrix locally |
| `report-run` | Render metrics from prediction and audit artifacts |

## GPU inference (Colab, S1+)

The real-model backend (`backend: transformers`) is an optional extra so local
mock/CPU runs and the test suite never pull in torch:

```bash
# In a GPU environment (e.g. Colab). torch ships with Colab; do not reinstall it.
pip install -e ".[gpu]"
ism validate-config --config configs/experiments/s1_qwen7b.yaml
ism run            --config configs/experiments/s1_qwen7b.yaml --output artifacts/runs/s1
```

`ism run` selects the backend from `model.backend` via
[`build_text_generator`](src/ism/inference/factory.py); the GPU adapter lives in
[transformers_backend.py](src/ism/inference/transformers_backend.py) and imports
torch/transformers lazily. `config_hash` is deployment-independent so local and
Colab agree (see [ADR 0001](docs/decisions/0001-config-hash-is-deployment-independent.md)).

Long runs are sharded with resume + merge for robustness against disconnects:
run `run-ablation` / `run-fixed-budget` per shard, then `merge-ablation` /
`merge-fixed-budget` into a single paired evaluation.

## Reproducing the paper results

Each experiment's raw artifacts (or SHA-256 hashes), environment, and exact
commands are recorded under [docs/evidence/](docs/evidence/README.md):

| Experiment | Evidence |
|---|---|
| 6.1 Dictionary Ablation (RQ1), N=240 | `docs/evidence/ablation-qwen7b-N120/` |
| 6.3 Fixed-Budget (RQ3), N=80 | `docs/evidence/fixed-budget-N40/` |
| 6.4 Reuse (RQ4) | `docs/evidence/reuse-N40/` |
| Filler-artifact sanity check | `docs/evidence/fixed-budget-filler-sanity/` |
| Compression diagnostics (v1–v3) | `docs/evidence/compress-audit-qwen7b-*/` |

## Documentation

- [Paper (PDF)](paper/ism-mixed-results.pdf) · [LaTeX source](paper/ism-mixed-results.tex)
- [Research draft](deep-research-report.md)
- [Implementation and validation plan](ism-system-plan.md)
- [Phase completion reports](docs/README.md)
