from __future__ import annotations

import random
import re
from dataclasses import dataclass

from ism.representation.models import ISMRepresentation, SymbolDefinition
from ism.representation.parser import serialize_ism
from ism.representation.tokenizer import TokenCounter


@dataclass(frozen=True)
class InterventionResult:
    representation: ISMRepresentation
    mapping: tuple[tuple[str, str], ...]
    seed: int | None


def remove_dictionary(source: ISMRepresentation) -> InterventionResult:
    return InterventionResult(
        representation=source.model_copy(update={"dictionary": ()}),
        mapping=(),
        seed=None,
    )


# Conclusion outcomes are written in upper/capitalized case (risk = HIGH,
# review = True) while condition values are lower case (marker_a = high), so a
# case-sensitive flip targets only the answer-bearing conclusions.
_CONCLUSION_FLIP = {
    "HIGH": "LOW",
    "LOW": "HIGH",
    "MEDIUM": "LOW",
    "True": "False",
    "False": "True",
    "TRUE": "FALSE",
    "FALSE": "TRUE",
}
_CONCLUSION_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_])(" + "|".join(_CONCLUSION_FLIP) + r")(?![A-Za-z0-9_])"
)


def _flip_conclusion_text(text: str) -> str:
    return _CONCLUSION_PATTERN.sub(lambda match: _CONCLUSION_FLIP[match.group(1)], text)


def flip_conclusions(source: ISMRepresentation) -> InterventionResult:
    """Counterfactual dictionary: invert conclusion outcomes (HIGH<->LOW,
    MEDIUM->LOW, True<->False) while keeping conditions and relations.

    Unlike derangement (which preserves the definition multiset), this changes
    the answer-bearing content, so it probes whether the dictionary *semantics*
    actually support the answer.
    """
    flipped = tuple(
        SymbolDefinition(label=item.label, definition=_flip_conclusion_text(item.definition))
        for item in source.dictionary
    )
    return InterventionResult(
        representation=source.model_copy(update={"dictionary": flipped}),
        mapping=tuple((item.label, item.label) for item in source.dictionary),
        seed=None,
    )


def blank_dictionary(
    source: ISMRepresentation, *, placeholder: str = "redacted"
) -> InterventionResult:
    """Strong dictionary removal: keep labels and relations but blank every
    definition. A sanity probe between Full Symbol + Dict and Symbol Only."""
    blanked = tuple(
        SymbolDefinition(label=item.label, definition=placeholder) for item in source.dictionary
    )
    return InterventionResult(
        representation=source.model_copy(update={"dictionary": blanked}),
        mapping=(),
        seed=None,
    )


def corrupt_dictionary(source: ISMRepresentation, *, seed: int) -> InterventionResult:
    if len(source.dictionary) < 2:
        raise ValueError("dictionary corruption requires at least two definitions")
    rng = random.Random(seed)
    indices = list(range(len(source.dictionary)))
    while True:
        rng.shuffle(indices)
        if all(index != replacement for index, replacement in enumerate(indices)):
            break
    corrupted = tuple(
        SymbolDefinition(
            label=item.label,
            definition=source.dictionary[indices[index]].definition,
        )
        for index, item in enumerate(source.dictionary)
    )
    mapping = tuple(
        (item.label, source.dictionary[indices[index]].label)
        for index, item in enumerate(source.dictionary)
    )
    return InterventionResult(
        representation=source.model_copy(update={"dictionary": corrupted}),
        mapping=mapping,
        seed=seed,
    )


def swap_labels(
    source: ISMRepresentation,
    *,
    new_labels: tuple[str, ...],
) -> InterventionResult:
    if len(new_labels) != len(source.symbols):
        raise ValueError("new label count must match symbol count")
    if len(new_labels) != len(set(new_labels)):
        raise ValueError("new labels must be unique")
    mapping = dict(zip(source.symbols, new_labels, strict=True))
    swapped_dictionary = tuple(
        SymbolDefinition(label=mapping[item.label], definition=item.definition)
        for item in source.dictionary
    )
    swapped_relations = tuple(_replace_labels(item, mapping) for item in source.relations)
    return InterventionResult(
        representation=ISMRepresentation(
            symbols=tuple(new_labels),
            dictionary=swapped_dictionary,
            relations=swapped_relations,
        ),
        mapping=tuple(mapping.items()),
        seed=None,
    )


def random_symbol_control(
    source: ISMRepresentation,
    *,
    seed: int,
    tokenizer: TokenCounter,
    tolerance: int = 0,
) -> InterventionResult:
    if tolerance < 0:
        raise ValueError("tolerance must not be negative")
    rng = random.Random(seed)
    generated_labels: list[str] = []
    while len(generated_labels) < len(source.symbols):
        label = f"R{rng.randrange(10_000_000):07d}"
        if label not in generated_labels:
            generated_labels.append(label)
    labels = tuple(generated_labels)

    relation = " ".join(labels)
    candidate = ISMRepresentation(symbols=labels, dictionary=(), relations=(relation,))
    target = tokenizer.count(serialize_ism(source))
    current = tokenizer.count(serialize_ism(candidate))
    if current > target + tolerance:
        raise ValueError("random control structural overhead exceeds target token length")
    noise: list[str] = []
    while current < target - tolerance:
        noise.append(f"n{rng.randrange(10_000):04d}")
        candidate = ISMRepresentation(
            symbols=labels,
            dictionary=(),
            relations=(f"{relation} {' '.join(noise)}",),
        )
        next_count = tokenizer.count(serialize_ism(candidate))
        if next_count <= current:
            raise ValueError("tokenizer did not increase length for random control padding")
        current = next_count
    final_count = tokenizer.count(serialize_ism(candidate))
    if abs(final_count - target) > tolerance:
        raise ValueError("could not match random control token length")
    if any(
        original in candidate_relation
        for original in source.relations
        for candidate_relation in candidate.relations
    ):
        raise ValueError("random control contains an original relation")
    return InterventionResult(
        representation=candidate,
        mapping=tuple(zip(source.symbols, labels, strict=True)),
        seed=seed,
    )


def _replace_labels(text: str, mapping: dict[str, str]) -> str:
    pattern = re.compile(
        r"(?<![A-Za-z0-9_])("
        + "|".join(map(re.escape, sorted(mapping, key=len, reverse=True)))
        + ")"
        r"(?![A-Za-z0-9_])"
    )
    return pattern.sub(lambda match: mapping[match.group(1)], text)
