#!/usr/bin/env python3
"""Build a compact two-column PDF preview for the ISM mixed-results paper.

The authoritative source is main.tex.  This renderer exists because the local
workspace does not include a TeX engine.  It uses reportlab from the bundled
Codex runtime and deliberately targets a polished two-page extended-abstract
layout.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    FrameBreak,
    Frame,
    PageTemplate,
    PageBreak,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


OUT = Path(__file__).with_name("ism-mixed-results.pdf")
PAGE_W, PAGE_H = letter
MARGIN_X = 0.55 * inch
MARGIN_Y = 0.48 * inch
GAP = 0.22 * inch
COL_W = (PAGE_W - 2 * MARGIN_X - GAP) / 2


def styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=15.5,
            leading=17.5,
            alignment=TA_CENTER,
            spaceAfter=5,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=10,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#555555"),
        ),
        "abstract_label": ParagraphStyle(
            "abstract_label",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.2,
            leading=9.5,
            alignment=TA_CENTER,
            spaceAfter=2,
        ),
        "abstract": ParagraphStyle(
            "abstract",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=8.0,
            leading=9.6,
            alignment=TA_JUSTIFY,
        ),
        "h1": ParagraphStyle(
            "h1",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=9.2,
            leading=10.5,
            spaceBefore=5,
            spaceAfter=2,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["BodyText"],
            fontName="Times-Roman",
            fontSize=8.15,
            leading=9.45,
            alignment=TA_JUSTIFY,
            spaceAfter=2.3,
        ),
        "small": ParagraphStyle(
            "small",
            parent=base["BodyText"],
            fontName="Times-Roman",
            fontSize=7.4,
            leading=8.4,
            alignment=TA_JUSTIFY,
            spaceAfter=2,
        ),
        "formula": ParagraphStyle(
            "formula",
            parent=base["BodyText"],
            fontName="Courier",
            fontSize=6.6,
            leading=7.4,
            leftIndent=4,
            spaceBefore=1,
            spaceAfter=2,
        ),
        "caption": ParagraphStyle(
            "caption",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=6.9,
            leading=7.8,
            textColor=colors.HexColor("#333333"),
            spaceBefore=2,
            spaceAfter=3,
        ),
        "ref": ParagraphStyle(
            "ref",
            parent=base["BodyText"],
            fontName="Times-Roman",
            fontSize=6.8,
            leading=7.6,
            leftIndent=8,
            firstLineIndent=-8,
            spaceAfter=1.4,
        ),
        "table": ParagraphStyle(
            "table",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=6.4,
            leading=7.2,
            alignment=TA_LEFT,
        ),
    }


S = styles()


class PipelineFigure(Flowable):
    def __init__(self, width: float) -> None:
        super().__init__()
        self.width = width
        self.height = 58

    def draw(self) -> None:
        c = self.canv
        labels = ["Long\ndocument", "LLM\ncompressor", "ISM\nS,D,G", "LLM\nreasoner"]
        box_w = (self.width - 36) / 4
        y = 18
        for i, label in enumerate(labels):
            x = i * (box_w + 12)
            c.setFillColor(colors.HexColor("#eef3fa"))
            c.setStrokeColor(colors.HexColor("#4d6f99"))
            c.roundRect(x, y, box_w, 27, 4, stroke=1, fill=1)
            c.setFillColor(colors.black)
            c.setFont("Helvetica-Bold", 5.8)
            for j, line in enumerate(label.split("\n")):
                c.drawCentredString(x + box_w / 2, y + 17 - 7 * j, line)
            if i < len(labels) - 1:
                ax = x + box_w + 2
                c.setStrokeColor(colors.HexColor("#555555"))
                c.line(ax, y + 13.5, ax + 8, y + 13.5)
                c.line(ax + 8, y + 13.5, ax + 4, y + 16.5)
                c.line(ax + 8, y + 13.5, ax + 4, y + 10.5)
        c.setFont("Helvetica", 6.2)
        c.setFillColor(colors.HexColor("#333333"))
        c.drawString(0, 4, "Figure 1. Prompt-only ISM: the LLM writes a structured text, and an LLM reads it again.")


class MiniLineChart(Flowable):
    def __init__(self, width: float) -> None:
        super().__init__()
        self.width = width
        self.height = 78

    def draw(self) -> None:
        c = self.canv
        x0, y0 = 18, 18
        w, h = self.width - 38, 42
        xs = [128, 256, 512]
        ys = [0.25, 0.3125, 0.375]
        c.setFont("Helvetica-Bold", 6.7)
        c.drawString(0, 67, "Figure 2. Summary minus ISM accuracy gap")
        c.setStrokeColor(colors.HexColor("#444444"))
        c.line(x0, y0, x0 + w, y0)
        c.line(x0, y0, x0, y0 + h)
        pts = []
        for x, y in zip(xs, ys):
            px = x0 + (x - 128) / (512 - 128) * w
            py = y0 + (y / 0.42) * h
            pts.append((px, py, x, y))
        c.setStrokeColor(colors.HexColor("#b33a3a"))
        c.setLineWidth(1.2)
        for p1, p2 in zip(pts, pts[1:]):
            c.line(p1[0], p1[1], p2[0], p2[1])
        c.setFillColor(colors.HexColor("#b33a3a"))
        c.setFont("Helvetica", 6)
        for px, py, x, y in pts:
            c.circle(px, py, 2.2, fill=1, stroke=0)
            c.setFillColor(colors.black)
            c.drawCentredString(px, y0 - 9, str(x))
            c.drawCentredString(px, py + 5, f"{y:.3f}")
            c.setFillColor(colors.HexColor("#b33a3a"))
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 5.7)
        c.drawString(x0 + w - 36, y0 - 18, "budget")


def p(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text, S[style])


def eq(text: str) -> Paragraph:
    return Paragraph(text, S["formula"])


def section(title: str) -> list[Flowable]:
    return [Paragraph(title, S["h1"])]


def compact_table(rows: list[list[str]], widths: list[float]) -> Table:
    table = Table(
        [[Paragraph(cell, S["table"]) for cell in row] for row in rows],
        colWidths=widths,
        hAlign="LEFT",
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e9edf3")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#c7c7c7")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 2.2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2),
                ("LEFTPADDING", (0, 0), (-1, -1), 2.3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2.3),
            ]
        )
    )
    return table


def first_page(canvas, doc) -> None:  # noqa: ANN001
    canvas.saveState()
    title = Paragraph(
        "Inspectable Symbolic Compression for Long-Context Reasoning:<br/>A Mixed-Results Study",
        S["title"],
    )
    title.wrapOn(canvas, PAGE_W - 2 * MARGIN_X, 40)
    title.drawOn(canvas, MARGIN_X, PAGE_H - 58)
    subtitle = Paragraph("Anonymous authors - English short-paper preview generated from the local study report", S["subtitle"])
    subtitle.wrapOn(canvas, PAGE_W - 2 * MARGIN_X, 14)
    subtitle.drawOn(canvas, MARGIN_X, PAGE_H - 78)
    canvas.setStrokeColor(colors.HexColor("#777777"))
    canvas.line(MARGIN_X, PAGE_H - 86, PAGE_W - MARGIN_X, PAGE_H - 86)
    canvas.restoreState()


def later_page(canvas, doc) -> None:  # noqa: ANN001
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#555555"))
    canvas.drawString(MARGIN_X, PAGE_H - 24, "Inspectable Symbolic Compression: A Mixed-Results Study")
    canvas.drawRightString(PAGE_W - MARGIN_X, PAGE_H - 24, str(doc.page))
    canvas.line(MARGIN_X, PAGE_H - 30, PAGE_W - MARGIN_X, PAGE_H - 30)
    canvas.restoreState()


def story() -> list[Flowable]:
    flow: list[Flowable] = []
    flow += [
        Paragraph("Abstract", S["abstract_label"]),
        Paragraph(
            "We study Inspectable Symbolic Compression (ISM), a prompt-only method that rewrites long "
            "documents as symbols, dictionary definitions, and relations. The result is mixed. ISM "
            "structure is functionally used: semantic dictionary damage and symbolic-structure removal "
            "both reduce accuracy. Yet a natural-language model summary is significantly more accurate "
            "and more token-efficient under the same budgets, and it dominates reuse cost-accuracy. "
            "We therefore do not claim prompt-only ISM is a better compressor. The study identifies a "
            "boundary: symbolic text written by an LLM and read by an LLM remains in the same class as "
            "summarization. Future work should treat ISM as executable semantic IR parsed and checked "
            "outside the LLM loop.",
            S["abstract"],
        ),
        Spacer(1, 3),
        PipelineFigure(COL_W),
    ]

    flow += section("1. Introduction")
    flow += [
        p(
            "Prompt-compression work usually optimizes token count and retained downstream accuracy. "
            "We ask a narrower diagnostic question: can a compressed representation expose meaning units "
            "that can be inspected and intervened on? ISM forces the compressor to emit symbols, a short "
            "dictionary, and relations such as precedence or exception.",
        ),
        p(
            "The original hypothesis was that this symbolic text would be both compact and manipulable. "
            "The experiments preserve only the second part. ISM is read and used by the model, but it "
            "does not beat ordinary summaries as a prompt-only compressor.",
        ),
    ]

    flow += section("2. Related Work")
    flow += [
        p(
            "<b>Token-level prompt compression.</b> LLMLingua, LongLLMLingua, LLMLingua-2, and Selective "
            "Context reduce context by selecting, reweighting, or dropping tokens. These methods are strong "
            "baselines for budgeted prompting, but the compressed object is still an optimized prompt span.",
            "small",
        ),
        p(
            "<b>Learned memory compression.</b> Gist Tokens, AutoCompressors, and ICAE replace long context "
            "with trained latent or soft-token memory. They can be very compact, but their internal state is "
            "not directly inspectable or locally editable by a human or a symbolic checker.",
            "small",
        ),
        p(
            "<b>Intervenable bottlenecks.</b> Concept Bottleneck and Concept Embedding Models show why an "
            "intermediate representation can be valuable even when it is not the shortest one: the user can "
            "inspect or intervene on named concepts. ISM imports that idea into prompt compression, but keeps "
            "the representation textual and prompt-only.",
            "small",
        ),
    ]

    flow += section("3. Method")
    flow += [
        p(
            "Each example contains a document x_i, questions q_ij, and labels y_ij. A producer m writes a "
            "compressed context z_i^m under budget B, and the same reasoner answers from that context.",
            "small",
        ),
        eq("z_i^m(B) = P_m(x_i; B),    tokens(z_i^m) &lt;= B"),
        eq("yhat_ij^m = R(z_i^m(B), q_ij)"),
        p(
            "ISM is the producer whose output is z=(S,D,G): symbol labels S={Z1,...,Zk}, dictionary entries "
            "D mapping each label to a condition and conclusion, and relations G encoding precedence, "
            "exception, or conjunction structure. Natural-language summary, keyword extraction, and oracle "
            "gold summary are evaluated under the same answer protocol.",
            "small",
        ),
        eq("Acc_m = mean[1(yhat_ij^m = y_ij)]"),
        eq("AR_m = Acc_m / Acc_full;    CR_m = tokens(z_m) / tokens(x)"),
        eq("ES_m = AR_m / CR_m;    Delta_flip = Acc_full_dict - Acc_flipped"),
        p(
            "Interventions separate three constructs. Derangement permutes labels while preserving the "
            "definition multiset; conclusion flip changes the semantic content of dictionary rules; blanking "
            "removes dictionary content; symbol-only and random-symbol controls test whether relations carry "
            "information beyond arbitrary markers.",
            "small",
        ),
    ]

    flow += section("4. Results")
    flow += [
        p("<b>RQ1: ISM structure is used.</b> After correcting a low-purity compressor and replacing weak "
          "label derangement with semantic conclusion flips, dictionary content and symbolic structure "
          "both show functional effects.", "small"),
        compact_table(
            [
                ["Condition", "Acc", "AR", "CR"],
                ["Full Context", "0.750", "1.000", "1.000"],
                ["Full Symbol+Dict", "0.446", "0.594", "0.745"],
                ["Flipped Dict", "0.367", "0.489", "0.745"],
                ["Symbol Only", "0.413", "0.550", "0.079"],
                ["Random Symbol", "0.304", "0.406", "0.738"],
            ],
            [78, 39, 39, 39],
        ),
        p(
            "Dev scale-up: Delta_map_flip=+0.079 (95% CI [0.013,0.146], p=0.032); "
            "Delta_symbol=+0.108 (95% CI [0.050,0.167], p=5e-4). Derangement is non-significant.",
            "caption",
        ),
        p("<b>RQ3: summaries beat ISM under fixed budgets.</b> The primary analysis is paired on the same "
          "80 questions, so it is not explained by full-context filler degradation.", "small"),
        compact_table(
            [
                ["Budget", "Summary-ISM", "95% CI", "p"],
                ["128", "+0.2500", "[0.100,0.400]", "0.0029"],
                ["256", "+0.3125", "[0.175,0.450]", "1.1e-4"],
                ["512", "+0.3750", "[0.250,0.500]", "2.3e-7"],
            ],
            [42, 64, 75, 42],
        ),
        MiniLineChart(COL_W),
    ]

    flow += [
        Spacer(1, 2),
        p(
            "Fixed-budget AR/ES cells show the same pattern. At budgets 128/256/512, Model Summary reaches "
            "1.036/51.3, 1.125/17.3, and 1.196/13.3, while ISM reaches 0.679/9.4, 0.679/9.3, and 0.661/8.9.",
            "small",
        ),
        p("<b>RQ4: reuse is not ISM-specific.</b> Cached representations become cheaper than full context "
          "from n=2 questions onward, but Model Summary is cheaper and more accurate than ISM.", "small"),
        compact_table(
            [
                ["Method", "n=1", "n=8", "n=64", "Acc"],
                ["Full Context", "1354", "10828", "86624", "0.700"],
                ["Model Summary", "1526", "2168", "7305", "0.787"],
                ["ISM", "1548", "2265", "8005", "0.475"],
                ["Keyword", "1820", "3492", "16868", "0.512"],
            ],
            [72, 39, 44, 48, 39],
        ),
        p(
            "<b>Takeaway.</b> The prompt-only format gives a real diagnostic signal but loses the "
            "efficiency contest. A stronger future paper should move from LLM-readable text to "
            "program-readable semantic IR.",
            "small",
        ),
        PageBreak(),
    ]

    flow += section("5. Discussion")
    flow += [
        p(
            "The positive result is that ISM is not inert: the model uses semantic dictionary content and "
            "symbolic relations. The negative result is stronger for the original compression claim: in the "
            "prompt-only setting, ISM and Model Summary are both LLM-written texts read by an LLM, and the "
            "ordinary summary is the better text cache.",
        ),
        p(
            "Thus the study should not be read as a successful new compressor. It is a boundary result. "
            "To become categorically different from summaries, ISM must be parsed, checked, transformed, "
            "and executed by programs outside the LLM. The future claim is not 'summaries cannot be edited' "
            "but 'semantic IRs permit automatic, local, schema-validated edits and symbolic execution.'",
        ),
    ]

    flow += section("6. Limitations")
    flow += [
        p(
            "The reported experiments are dev-scale and synthetic. QASPER and LLMLingua-2 are specified but "
            "not fully evaluated here. Several large GPU artifacts are stored by sha256 and reproducibility "
            "commands. RQ2 dictionary swap remains future work. Most importantly, this paper evaluates "
            "prompt-only ISM, not a parser/checker/executor system.",
            "small",
        )
    ]

    flow += section("7. Conclusion")
    flow += [
        p(
            "ISM representations are functionally used, but prompt-only ISM is not a better compressor than "
            "natural-language summaries. This mixed result closes one path and clarifies the next: executable "
            "semantic IR for long-context reasoning.",
        ),
        p(
            "The boundary claim is therefore precise: structured prompt text can expose units that an LLM "
            "uses, but it does not by itself create a new computational object. The next version must make "
            "the representation parseable, checkable, and executable by ordinary software.",
            "small",
        ),
    ]
    flow += section("8. Pre-registered Status")
    flow += [
        compact_table(
            [
                ["Criterion", "Status", "Evidence"],
                ["#1 ISM > Summary", "Failed", "RQ3/RQ4 summary dominates"],
                ["#2 structure used", "Met", "flip p=0.032; symbol p=5e-4"],
                ["#3 unseen swap", "Open", "LoRA swap not run"],
            ],
            [74, 42, 106],
        ),
        p(
            "By the original decision rule, failure of criterion #1 means the paper cannot claim "
            "an efficiency advantage for ISM. Criterion #2 supports functional use of the internal "
            "structure, but that is distinct from being a better compressor.",
            "small",
        ),
    ]

    flow.append(FrameBreak())

    flow += section("9. Semantic-IR Path")
    flow += [
        compact_table(
            [
                ["Property", "Summary", "Semantic IR"],
                ["Format", "free text", "schema / AST"],
                ["Validation", "manual", "checker"],
                ["Edit", "rewrite", "rule-id local edit"],
                ["Execution", "LLM", "symbolic executor"],
            ],
            [58, 72, 92],
        ),
        p(
            "The next research question is compile-and-execute: can an LLM compile a long document "
            "into an IR that a non-LLM program can parse and run? That would make the representation "
            "categorically different from a short natural-language summary.",
            "small",
        ),
    ]

    flow += section("10. Evidence Ledger")
    flow += [
        compact_table(
            [
                ["Finding", "Evidence", "Status"],
                ["ISM is used", "ablation-qwen7b-N120", "positive"],
                ["Summary wins", "fixed-budget-N40", "negative"],
                ["Reuse not unique", "reuse-N40", "negative"],
                ["Root cause", "llm-ism-diagnostic", "resolved"],
            ],
            [58, 98, 66],
        ),
        p(
            "The evidence pattern is internally consistent: the representation carries signal, but the "
            "prompt-only implementation loses the efficiency contest to a plain summary.",
            "small",
        ),
    ]

    flow += section("11. Next Tests")
    flow += [
        p(
            "<b>Compile-and-execute.</b> Convert ISM text into a schema-checked AST and answer with a "
            "deterministic executor. <b>Targeted edits.</b> Repair or delete a rule by id and verify the "
            "prediction changes locally. <b>Swap.</b> Finish the LoRA dictionary-swap experiment for unseen "
            "labels.",
            "small",
        )
    ]

    flow += section("12. Reproducibility")
    flow += [
        p(
            "Evidence is stored under docs/evidence/: ablation-qwen7b-N120 for RQ1, fixed-budget-N40 "
            "for RQ3, reuse-N40 for RQ4, and llm-ism-diagnostic.md for the corruption/purity diagnosis. "
            "Large GPU outputs are retained by sha256 and reproducibility commands.",
            "small",
        )
    ]

    flow += section("References")
    refs = [
        "[1] Koh et al. Concept Bottleneck Models. ICML 2020.",
        "[2] Espinosa Zarlenga et al. Concept Embedding Models. NeurIPS 2022.",
        "[3] Dasigi et al. QASPER: QA anchored in research papers. NAACL 2021.",
        "[4] Jiang et al. LLMLingua. EMNLP 2023.",
        "[5] Jiang et al. LongLLMLingua. ACL 2024.",
        "[6] Pan et al. LLMLingua-2. Findings ACL 2024.",
        "[7] Mu et al. Learning to Compress Prompts with Gist Tokens. NeurIPS 2023.",
        "[8] Chevalier et al. Adapting Language Models to Compress Contexts. EMNLP 2023.",
        "[9] Ge et al. In-context Autoencoder. ICLR 2024.",
        "[10] McNemar. Sampling error of correlated proportions. Psychometrika 1947.",
    ]
    flow.extend(Paragraph(r, S["ref"]) for r in refs)
    return flow


def build() -> None:
    first_top = PAGE_H - 1.72 * inch
    normal_top = PAGE_H - MARGIN_Y
    first_frames = [
        Frame(MARGIN_X, MARGIN_Y, COL_W, first_top - MARGIN_Y, id="f1a", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0),
        Frame(MARGIN_X + COL_W + GAP, MARGIN_Y, COL_W, first_top - MARGIN_Y, id="f1b", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0),
    ]
    normal_frames = [
        Frame(MARGIN_X, MARGIN_Y, COL_W, normal_top - MARGIN_Y - 0.08 * inch, id="n1", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0),
        Frame(MARGIN_X + COL_W + GAP, MARGIN_Y, COL_W, normal_top - MARGIN_Y - 0.08 * inch, id="n2", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0),
    ]
    doc = BaseDocTemplate(
        str(OUT),
        pagesize=letter,
        leftMargin=MARGIN_X,
        rightMargin=MARGIN_X,
        topMargin=MARGIN_Y,
        bottomMargin=MARGIN_Y,
    )
    doc.addPageTemplates(
        [
            PageTemplate(id="first", frames=first_frames, onPage=first_page, autoNextPageTemplate="later"),
            PageTemplate(id="later", frames=normal_frames, onPage=later_page),
        ]
    )
    doc.build(story())


if __name__ == "__main__":
    build()
    print(OUT)
