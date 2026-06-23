#!/usr/bin/env python3
"""Generate a dependency-free PDF preview of the ISM mixed-results paper.

The workspace does not include a TeX engine, so this script writes a compact
PDF directly using standard PDF text and drawing operators.  The authoritative
paper source remains main.tex.
"""

from __future__ import annotations

import math
import textwrap
from dataclasses import dataclass, field
from pathlib import Path


PAGE_W = 612
PAGE_H = 792
MARGIN = 54


def esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


@dataclass
class Page:
    ops: list[str] = field(default_factory=list)

    def text(self, x: float, y: float, text: str, size: int = 10, font: str = "F1") -> None:
        self.ops.append(f"BT /{font} {size} Tf {x:.2f} {y:.2f} Td ({esc(text)}) Tj ET")

    def line(self, x1: float, y1: float, x2: float, y2: float, width: float = 0.6) -> None:
        self.ops.append(f"{width:.2f} w {x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S")

    def rect(self, x: float, y: float, w: float, h: float, gray: float | None = None) -> None:
        if gray is not None:
            self.ops.append(f"{gray:.2f} g {x:.2f} {y:.2f} {w:.2f} {h:.2f} re f 0 g")
        else:
            self.ops.append(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re S")

    def fill_rect_rgb(self, x: float, y: float, w: float, h: float, r: float, g: float, b: float) -> None:
        self.ops.append(f"{r:.2f} {g:.2f} {b:.2f} rg {x:.2f} {y:.2f} {w:.2f} {h:.2f} re f 0 0 0 rg")


class Document:
    def __init__(self) -> None:
        self.pages: list[Page] = []

    def page(self) -> Page:
        page = Page()
        self.pages.append(page)
        return page

    def write(self, path: Path) -> None:
        objects: list[bytes] = []

        def add(obj: str | bytes) -> int:
            data = obj.encode("latin-1") if isinstance(obj, str) else obj
            objects.append(data)
            return len(objects)

        font_helv = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        font_bold = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
        font_cour = add("<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>")

        page_ids: list[int] = []
        for page in self.pages:
            stream = "\n".join(page.ops).encode("latin-1", "replace")
            content_id = add(
                b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream"
            )
            page_id = add(
                f"<< /Type /Page /Parent 0 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] "
                f"/Resources << /Font << /F1 {font_helv} 0 R /F2 {font_bold} 0 R /F3 {font_cour} 0 R >> >> "
                f"/Contents {content_id} 0 R >>"
            )
            page_ids.append(page_id)

        kids = " ".join(f"{pid} 0 R" for pid in page_ids)
        pages_id = add(f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>")

        # Patch parent references now that the pages object exists.
        for pid in page_ids:
            objects[pid - 1] = objects[pid - 1].replace(b"/Parent 0 0 R", f"/Parent {pages_id} 0 R".encode("ascii"))

        catalog_id = add(f"<< /Type /Catalog /Pages {pages_id} 0 R >>")

        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for i, obj in enumerate(objects, 1):
            offsets.append(len(out))
            out.extend(f"{i} 0 obj\n".encode("ascii"))
            out.extend(obj)
            out.extend(b"\nendobj\n")
        xref = len(out)
        out.extend(f"xref\n0 {len(objects)+1}\n".encode("ascii"))
        out.extend(b"0000000000 65535 f \n")
        for off in offsets[1:]:
            out.extend(f"{off:010d} 00000 n \n".encode("ascii"))
        out.extend(
            f"trailer << /Size {len(objects)+1} /Root {catalog_id} 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii")
        )
        path.write_bytes(out)


def wrapped(page: Page, x: float, y: float, text: str, width: int = 88, size: int = 10, leading: int = 13) -> float:
    for para in text.split("\n"):
        if not para.strip():
            y -= leading
            continue
        for line in textwrap.wrap(para, width=width):
            page.text(x, y, line, size=size)
            y -= leading
    return y


def heading(page: Page, y: float, text: str) -> float:
    page.text(MARGIN, y, text, size=14, font="F2")
    page.line(MARGIN, y - 4, PAGE_W - MARGIN, y - 4, width=0.8)
    return y - 20


def table(page: Page, x: float, y: float, rows: list[list[str]], widths: list[float], row_h: float = 18) -> float:
    total = sum(widths)
    page.rect(x, y - row_h, total, row_h, gray=0.9)
    cur_y = y
    for r, row in enumerate(rows):
        cur_x = x
        if r == 1:
            page.line(x, cur_y, x + total, cur_y, width=0.8)
        for c, cell in enumerate(row):
            font = "F2" if r == 0 else "F1"
            page.text(cur_x + 4, cur_y - 12, cell[:42], size=8, font=font)
            cur_x += widths[c]
        cur_y -= row_h
    page.line(x, y, x + total, y, width=0.8)
    page.line(x, cur_y, x + total, cur_y, width=0.8)
    return cur_y - 14


def bar_chart(page: Page, x: float, y: float, title: str, labels: list[str], values: list[float], max_v: float) -> None:
    page.text(x, y, title, size=11, font="F2")
    base_y = y - 145
    chart_h = 110
    page.line(x, base_y, x + 250, base_y)
    page.line(x, base_y, x, base_y + chart_h)
    for i, (label, value) in enumerate(zip(labels, values)):
        bx = x + 25 + i * 70
        h = chart_h * value / max_v
        page.fill_rect_rgb(bx, base_y, 34, h, 0.18, 0.36, 0.64)
        page.text(bx - 5, base_y - 14, label, size=8)
        page.text(bx - 2, base_y + h + 4, f"{value:.3f}", size=8)


def line_chart(page: Page, x: float, y: float, title: str, xs: list[int], ys: list[float], max_y: float) -> None:
    page.text(x, y, title, size=11, font="F2")
    base_y = y - 145
    chart_w = 250
    chart_h = 110
    page.line(x, base_y, x + chart_w, base_y)
    page.line(x, base_y, x, base_y + chart_h)
    points: list[tuple[float, float]] = []
    min_x, max_x = min(xs), max(xs)
    for xi, yi in zip(xs, ys):
        px = x + (xi - min_x) / (max_x - min_x) * chart_w
        py = base_y + yi / max_y * chart_h
        points.append((px, py))
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        page.line(x1, y1, x2, y2, width=1.2)
    for (px, py), xi, yi in zip(points, xs, ys):
        page.fill_rect_rgb(px - 2.5, py - 2.5, 5, 5, 0.80, 0.20, 0.16)
        page.text(px - 8, base_y - 14, str(xi), size=8)
        page.text(px - 8, py + 7, f"{yi:.3f}", size=8)


def pipeline(page: Page, x: float, y: float) -> None:
    boxes = [
        ("Long\ndocument", x, y),
        ("LLM\ncompressor", x + 115, y),
        ("Symbols +\ndictionary", x + 230, y),
        ("LLM\nreasoner", x + 365, y),
    ]
    for text, bx, by in boxes:
        page.rect(bx, by - 52, 86, 42, gray=0.92)
        for j, line in enumerate(text.split("\n")):
            page.text(bx + 8, by - 25 - 11 * j, line, size=9, font="F2" if j == 0 else "F1")
    for bx in [x + 86, x + 201, x + 316]:
        page.line(bx, y - 31, bx + 28, y - 31, width=1.2)
        page.line(bx + 28, y - 31, bx + 22, y - 27, width=1.2)
        page.line(bx + 28, y - 31, bx + 22, y - 35, width=1.2)
    page.rect(x + 230, y - 105, 120, 34, gray=0.95)
    page.text(x + 238, y - 91, "flip / blank / derange", size=8)
    page.line(x + 273, y - 52, x + 273, y - 71, width=1.0)


def build() -> Document:
    doc = Document()

    p = doc.page()
    p.text(MARGIN, 735, "Inspectable Symbolic Compression for Long-Context Reasoning", 18, "F2")
    p.text(MARGIN, 712, "A Mixed-Results Study", 15, "F2")
    p.text(MARGIN, 690, "Anonymous Authors", 10)
    y = heading(p, 655, "Abstract")
    y = wrapped(
        p,
        MARGIN,
        y,
        "We study Inspectable Symbolic Compression (ISM), a prompt-only method that rewrites "
        "long documents as discrete symbols, dictionary definitions, and symbolic relations. "
        "The result is mixed. ISM structure is functionally used: flipping dictionary conclusions "
        "and removing symbolic structure significantly reduce accuracy. However, natural-language "
        "model summaries are significantly more accurate and more token-efficient under the same "
        "fixed budgets, and they dominate the reuse cost-accuracy frontier. We therefore do not "
        "claim that prompt-only ISM is a better compressor. The study instead identifies a boundary: "
        "symbolic compression generated by an LLM and read by an LLM remains in the same class as "
        "text summarization, pointing toward future executable semantic IRs.",
        width=86,
    )
    y = heading(p, y - 8, "Summary of Findings")
    rows = [
        ["RQ", "Result", "Interpretation"],
        ["RQ1", "ISM dictionary and symbolic structure are used.", "Positive"],
        ["RQ3", "Model Summary beats ISM at all budgets.", "Negative"],
        ["RQ4", "Reuse helps caches, but summary dominates ISM.", "Negative"],
        ["RQ2", "Unseen-label swap remains unrun.", "Future work"],
    ]
    y = table(p, MARGIN, y, rows, [55, 300, 115], row_h=19)
    p.text(MARGIN, y, "Figure 1: Prompt-only ISM pipeline.", 10, "F2")
    pipeline(p, MARGIN, y - 20)

    p = doc.page()
    y = heading(p, 735, "Method and Setup")
    y = wrapped(
        p,
        MARGIN,
        y,
        "ISM represents a compressed document as symbols S, a dictionary D mapping symbols to "
        "short definitions, and relations G encoding precedence, exception, or application order. "
        "The main model is Qwen2.5-7B-Instruct in 4-bit inference with greedy decoding. "
        "Compression outputs are regenerated rather than truncated when they exceed budget. "
        "Synthetic Rule-QA provides hidden rule graphs for audit and oracle summaries.",
        width=88,
    )
    y = heading(p, y - 10, "RQ1: Dictionary Ablation")
    rows = [
        ["Condition", "Acc", "AR", "CR"],
        ["Full Context", "0.750", "1.000", "1.000"],
        ["Full Symbol + Dict", "0.446", "0.594", "0.745"],
        ["Deranged Dict", "0.375", "0.500", "0.745"],
        ["Flipped Dict", "0.367", "0.489", "0.745"],
        ["Symbol Only", "0.413", "0.550", "0.079"],
        ["Random Symbol", "0.304", "0.406", "0.738"],
    ]
    y = table(p, MARGIN, y, rows, [190, 70, 70, 70], row_h=18)
    wrapped(
        p,
        MARGIN,
        y,
        "At N=240 paired questions, semantic dictionary flip is positive and significant "
        "(Delta_map_flip=+0.079, p=0.032), and Symbol Only beats Random Symbol "
        "(Delta_symbol=+0.108, p=0.0005). Derangement is not significant, indicating "
        "that surface label binding is not the main mechanism.",
        width=88,
    )
    bar_chart(p, 300, 215, "RQ1 contrast estimates", ["derange", "flip", "symbol"], [0.071, 0.079, 0.108], 0.14)

    p = doc.page()
    y = heading(p, 735, "RQ3: Fixed-Budget Comparison")
    rows = [
        ["Method", "128", "256", "512"],
        ["Oracle Gold Summary", "0.732 / 11.0", "0.732 / 11.0", "0.732 / 11.0"],
        ["Model Summary", "1.036 / 51.3", "1.125 / 17.3", "1.196 / 13.3"],
        ["Keyword Extract", "0.714 / 7.4", "0.732 / 4.2", "0.750 / 3.6"],
        ["ISM", "0.679 / 9.4", "0.679 / 9.3", "0.661 / 8.9"],
    ]
    y = table(p, MARGIN, y, rows, [155, 110, 110, 110], row_h=20)
    rows = [
        ["Budget", "Summary-ISM", "95% CI", "McNemar p"],
        ["128", "+0.2500", "[0.100, 0.400]", "0.0029"],
        ["256", "+0.3125", "[0.175, 0.450]", "1.1e-4"],
        ["512", "+0.3750", "[0.250, 0.500]", "2.3e-7"],
    ]
    y = table(p, MARGIN, y - 5, rows, [80, 120, 150, 110], row_h=20)
    wrapped(
        p,
        MARGIN,
        y,
        "The primary paired comparison is on the same 80 questions. Model Summary significantly "
        "outperforms ISM at every budget. Since both methods remove filler, this result is not "
        "explained by full-context degradation.",
        width=88,
    )
    line_chart(p, 300, 215, "Summary accuracy advantage", [128, 256, 512], [0.25, 0.3125, 0.375], 0.42)

    p = doc.page()
    y = heading(p, 735, "RQ4: Reuse Cost-Accuracy")
    rows = [
        ["Method", "n=1", "n=8", "n=32", "n=64", "Acc"],
        ["Full Context", "1354", "10828", "43312", "86624", "0.700"],
        ["Model Summary", "1526", "2168", "4369", "7305", "0.787"],
        ["ISM", "1548", "2265", "4725", "8005", "0.475"],
        ["Oracle Gold", "1530", "2184", "4428", "7420", "0.512"],
        ["Keyword Extract", "1820", "3492", "9225", "16868", "0.512"],
    ]
    y = table(p, MARGIN, y, rows, [130, 65, 75, 85, 85, 55], row_h=19)
    wrapped(
        p,
        MARGIN,
        y,
        "All cached methods become cheaper than full context from two questions onward. "
        "However, Model Summary is both cheaper and more accurate than ISM, so reuse is "
        "not an ISM-specific advantage. It is a property of any reusable text cache.",
        width=88,
    )
    y = heading(p, 335, "Discussion")
    wrapped(
        p,
        MARGIN,
        y,
        "What worked: ISM structure is used by the LLM. What failed: the original efficiency "
        "hypothesis. Prompt-only ISM is generated by an LLM and read by an LLM, just like "
        "a summary; within that class, ordinary summaries are stronger. The follow-up path is "
        "not another prompt format but a program-readable semantic IR with parser, checker, "
        "local transformations, and symbolic execution.",
        width=88,
    )

    p = doc.page()
    y = heading(p, 735, "Limitations and Conclusion")
    y = wrapped(
        p,
        MARGIN,
        y,
        "The experiments are dev-scale and synthetic. QASPER and LLMLingua-2 are specified "
        "but not fully run in the reported results. Several GPU raw files are retained by "
        "hash and reproducibility commands rather than fully stored in the repository. "
        "Most importantly, this paper evaluates prompt-only ISM, not an executable semantic IR.",
        width=88,
    )
    y = wrapped(
        p,
        MARGIN,
        y - 8,
        "Conclusion: ISM is functionally used but is not a better prompt-only compressor than "
        "natural-language summaries. The honest contribution is a mixed result that maps the "
        "failure mode and points toward executable semantic IRs outside the LLM-only loop.",
        width=88,
    )
    y = heading(p, y - 10, "Selected References")
    refs = [
        "Koh et al. Concept Bottleneck Models. ICML 2020.",
        "Dasigi et al. QASPER: QA anchored in research papers. NAACL 2021.",
        "Jiang et al. LLMLingua. arXiv:2310.05736, 2023.",
        "Jiang et al. LongLLMLingua. arXiv:2310.06839, 2023.",
        "Pan et al. LLMLingua-2. arXiv:2403.12968, 2024.",
        "Mu et al. Learning to Compress Prompts with Gist Tokens. NeurIPS 2023.",
        "Chevalier et al. Adapting Language Models to Compress Contexts. arXiv:2305.14788.",
    ]
    for ref in refs:
        y = wrapped(p, MARGIN + 12, y, "- " + ref, width=86, size=9, leading=12)
    return doc


def main() -> None:
    out = Path(__file__).with_name("ism-mixed-results.pdf")
    build().write(out)
    print(out)


if __name__ == "__main__":
    main()

