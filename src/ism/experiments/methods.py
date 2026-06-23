"""Fixed-Budget comparison methods (paper 6.3 / RQ3).

Each producer maps a document to a context string within a token budget B
(whitespace tokens, the shared budget unit). Budget fairness: outputs are kept
within B by *selection or regeneration*, never mid-token truncation. LLMLingua-2
is intentionally omitted from this first version (left as a follow-up baseline).
"""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Sequence

from ism.data.generator import GeneratedDocument
from ism.data.render import render_rule
from ism.experiments.compressor import CompressionError, LlmCompressor
from ism.inference.contracts import GenerationRequest, TextGenerator
from ism.representation.parser import serialize_ism
from ism.representation.tokenizer import TokenCounter

_WORD = re.compile(r"[A-Za-z0-9_.]+")
_STOPWORDS = frozenset({
    "the", "a", "an", "of", "to", "and", "or", "if", "then", "is", "are", "has",
    "have", "for", "at", "in", "on", "with", "not", "than", "be", "by", "as",
    "that", "this", "these", "those", "it", "its",
})

FIXED_BUDGET_METHODS = (
    "full_context",
    "ism",
    "model_summary",
    "keyword_extract",
    "oracle_gold_summary",
)


def full_context_text(document: GeneratedDocument) -> str:
    """Uncompressed baseline (CR = 1); budget does not apply."""
    return document.document_text


def compute_idf(documents: Sequence[GeneratedDocument]) -> dict[str, float]:
    """Smoothed inverse document frequency over the experiment corpus."""
    n = len(documents)
    df: Counter[str] = Counter()
    for document in documents:
        for token in set(_WORD.findall(document.document_text.casefold())):
            df[token] += 1
    return {token: math.log((1 + n) / (1 + count)) + 1.0 for token, count in df.items()}


def keyword_extract_text(
    document: GeneratedDocument,
    *,
    budget: int,
    idf: dict[str, float],
) -> str:
    """TF-IDF keyword selection: highest-scoring distinct tokens up to budget.

    Deterministic and GPU-free. Selection (top-k tokens), never mid-token cut.
    """
    tokens = _WORD.findall(document.document_text.casefold())
    tf: Counter[str] = Counter(t for t in tokens if t not in _STOPWORDS and len(t) > 1)
    scored = sorted(
        tf.items(),
        key=lambda item: (-(item[1] * idf.get(item[0], 1.0)), item[0]),
    )
    return " ".join(token for token, _ in scored[:budget])


def oracle_gold_summary_text(document: GeneratedDocument, *, budget: int) -> str:
    """Upper-bound reference: gold rules rendered to NL, whole rules up to budget.

    Not a usable method — a sanity ceiling (paper 5.3).
    """
    selected: list[str] = []
    used = 0
    for rule in document.graph.rules:
        rendered = render_rule(rule)
        cost = len(rendered.split())
        if used + cost > budget:
            continue
        selected.append(rendered)
        used += cost
    return " ".join(selected)


def model_summary_text(
    document: GeneratedDocument,
    *,
    budget: int,
    generator: TextGenerator,
    seed: int,
    max_attempts: int,
    max_new_tokens: int,
    tokenizer: TokenCounter,
) -> str:
    """Same-model natural-language summary within budget (regenerate on overflow).

    The key ISM control: same LLM, same budget, same regeneration rule.
    """
    nudge = ""
    last = "no attempts"
    for attempt in range(max_attempts):
        prompt = (
            f"Summarize the document for question answering in at most {budget} "
            "whitespace-separated words. Preserve every condition, threshold, "
            "exception, priority, and conclusion. Output only the summary.\n"
            f"{nudge}\nDocument:\n{document.document_text}\n"
        )
        request = GenerationRequest(
            request_id=f"{document.document_id}:summary:{attempt}",
            prompt=prompt,
            max_new_tokens=max_new_tokens,
            seed=seed + attempt,
        )
        (result,) = generator.generate((request,))
        if not result.succeeded or result.text is None:
            last = result.error_message or "generation failed"
            nudge = f"Your previous output failed ({last}); retry."
            continue
        text = " ".join(result.text.split())
        if not text:
            last = "empty"
            nudge = "Your previous output was empty; produce a summary."
            continue
        if tokenizer.count(text) > budget:
            last = "budget_exceeded"
            nudge = f"Your previous summary exceeded {budget} words; be shorter."
            continue
        return text
    raise CompressionError(f"{document.document_id}: no within-budget summary ({last})")


def ism_text(
    document: GeneratedDocument,
    *,
    budget: int,
    compressor: LlmCompressor,
) -> str:
    """ISM compression serialized to text (already budget-validated by parse)."""
    return serialize_ism(compressor.compress(document, budget=budget).representation)


__all__ = [
    "FIXED_BUDGET_METHODS",
    "compute_idf",
    "full_context_text",
    "ism_text",
    "keyword_extract_text",
    "model_summary_text",
    "oracle_gold_summary_text",
]
