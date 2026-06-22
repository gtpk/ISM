# ISM Research

Implementation workspace for the Inspectable Symbolic Compression experiments.

## Local setup

```bash
uv sync --dev
uv run ism validate-config --config configs/experiments/smoke.yaml
uv run ism dry-run --config configs/experiments/smoke.yaml
uv run pytest
```

The local repository is the source of truth. Colab is used only after local blocking tests pass.

## Documentation

- [Research draft](deep-research-report.md)
- [Implementation and validation plan](ism-system-plan.md)
- [Phase completion reports](docs/README.md)
