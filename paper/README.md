# ISM Mixed-Results Paper

This directory contains the English paper draft and a generated PDF artifact.

- `main.tex` - LaTeX source for the paper.
- `references.bib` - bibliography entries used by `main.tex`.
- `build_pdf.py` - two-column PDF renderer used in this workspace, because no
  TeX engine is installed locally.
- `ism-mixed-results.pdf` - generated two-column PDF preview of the paper content.

To compile the LaTeX source on a machine with a TeX distribution:

```bash
pdflatex main
bibtex main
pdflatex main
pdflatex main
```

To regenerate the local PDF preview without TeX, use a Python environment with
`reportlab` installed. In the Codex desktop workspace, the bundled runtime works:

```bash
/Users/puka/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 build_pdf.py
```
