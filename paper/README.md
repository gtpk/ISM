# ISM Mixed-Results Paper

This directory contains the English paper draft and a generated PDF artifact.

- `main.tex` - LaTeX source for the paper.
- `references.bib` - bibliography entries used by `main.tex`.
- `build_pdf.py` - dependency-free PDF renderer used in this workspace, because no
  TeX engine is installed locally.
- `ism-mixed-results.pdf` - generated PDF preview of the paper content.

To compile the LaTeX source on a machine with a TeX distribution:

```bash
pdflatex main
bibtex main
pdflatex main
pdflatex main
```

To regenerate the local PDF preview without TeX:

```bash
python3 build_pdf.py
```
