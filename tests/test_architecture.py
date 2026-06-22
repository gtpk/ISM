from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_IMPORTS = {"bitsandbytes", "google.colab", "transformers"}
PURE_MODULE_PATHS = {"config.py", "planning.py", "data", "representation"}


def test_p0_arc_001_pure_modules_do_not_import_gpu_or_colab_packages() -> None:
    package_root = Path("src/ism")
    violations: list[str] = []

    paths: list[Path] = []
    for relative_path in PURE_MODULE_PATHS:
        candidate = package_root / relative_path
        paths.extend(candidate.rglob("*.py") if candidate.is_dir() else [candidate])

    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            imported: list[str] = []
            if isinstance(node, ast.Import):
                imported = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported = [node.module]
            for name in imported:
                if any(name == item or name.startswith(f"{item}.") for item in FORBIDDEN_IMPORTS):
                    violations.append(f"{path}:{getattr(node, 'lineno', '?')}: {name}")

    assert not violations, "\n".join(violations)
