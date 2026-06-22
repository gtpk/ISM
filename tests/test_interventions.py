from __future__ import annotations

import hashlib
import random

import pytest

from ism.representation.interventions import (
    corrupt_dictionary,
    random_symbol_control,
    remove_dictionary,
    swap_labels,
)
from ism.representation.models import ISMRepresentation, SymbolDefinition
from ism.representation.parser import serialize_ism
from ism.representation.tokenizer import WhitespaceTokenCounter


def source_representation() -> ISMRepresentation:
    return ISMRepresentation(
        symbols=("Z1", "Z2", "Z3"),
        dictionary=(
            SymbolDefinition(label="Z1", definition="marker high"),
            SymbolDefinition(label="Z2", definition="repair active"),
            SymbolDefinition(label="Z3", definition="event ordered"),
        ),
        relations=("Z1 and !Z2 => Z3", "Z3 => HIGH"),
    )


def relation_hash(value: ISMRepresentation) -> str:
    return hashlib.sha256("\n".join(value.relations).encode()).hexdigest()


def test_p2_fun_003_remove_only_changes_dictionary() -> None:
    source = source_representation()
    before = source.model_dump_json()

    result = remove_dictionary(source)

    assert result.representation.dictionary == ()
    assert result.representation.symbols == source.symbols
    assert relation_hash(result.representation) == relation_hash(source)
    assert source.model_dump_json() == before


def test_p2_fun_004_corruption_is_a_derangement() -> None:
    source = source_representation()

    result = corrupt_dictionary(source, seed=42)

    original = source.definition_map()
    corrupted = result.representation.definition_map()
    assert set(corrupted.values()) == set(original.values())
    assert all(corrupted[label] != original[label] for label in source.symbols)
    assert result.representation.relations == source.relations


def test_p2_fun_005_single_symbol_corruption_fails_without_retry_loop() -> None:
    source = ISMRepresentation(
        symbols=("Z1",),
        dictionary=(SymbolDefinition(label="Z1", definition="only"),),
        relations=("Z1",),
    )

    with pytest.raises(ValueError, match="at least two"):
        corrupt_dictionary(source, seed=42)


def test_p2_fun_006_swap_is_a_total_bijection() -> None:
    source = source_representation()

    result = swap_labels(source, new_labels=("Q7", "Q8", "Q9"))

    assert result.representation.symbols == ("Q7", "Q8", "Q9")
    assert {item.label for item in result.representation.dictionary} == {"Q7", "Q8", "Q9"}
    assert result.representation.referenced_labels() == {"Q7", "Q8", "Q9"}
    assert dict(result.mapping) == {"Z1": "Q7", "Z2": "Q8", "Z3": "Q9"}


def test_p2_fun_007_swap_inverse_restores_original() -> None:
    source = source_representation()
    swapped = swap_labels(source, new_labels=("Q7", "Q8", "Q9")).representation

    restored = swap_labels(swapped, new_labels=source.symbols).representation

    assert restored == source


def test_p2_fun_008_random_control_matches_shape_and_token_length() -> None:
    source = source_representation()
    tokenizer = WhitespaceTokenCounter()

    result = random_symbol_control(source, seed=42, tokenizer=tokenizer)

    assert len(result.representation.symbols) == len(source.symbols)
    assert result.representation.dictionary == ()
    assert tokenizer.count(serialize_ism(result.representation)) == tokenizer.count(
        serialize_ism(source)
    )
    assert not set(result.representation.relations) & set(source.relations)


def test_p2_det_001_interventions_are_seed_deterministic() -> None:
    source = source_representation()
    tokenizer = WhitespaceTokenCounter()

    first_corrupt = corrupt_dictionary(source, seed=42)
    second_corrupt = corrupt_dictionary(source, seed=42)
    first_random = random_symbol_control(source, seed=42, tokenizer=tokenizer)
    second_random = random_symbol_control(source, seed=42, tokenizer=tokenizer)

    assert first_corrupt == second_corrupt
    assert first_random == second_random


def test_swap_rejects_non_bijection() -> None:
    source = source_representation()

    with pytest.raises(ValueError, match="unique"):
        swap_labels(source, new_labels=("Q1", "Q1", "Q2"))


def test_phase2_1000_random_representations_preserve_invariants() -> None:
    rng = random.Random(42)
    tokenizer = WhitespaceTokenCounter()

    for index in range(1000):
        labels = tuple(f"Z{index * 3 + offset + 1}" for offset in range(3))
        source = ISMRepresentation(
            symbols=labels,
            dictionary=tuple(
                SymbolDefinition(
                    label=label,
                    definition=f"feature {rng.randrange(1000)} value {rng.randrange(1000)}",
                )
                for label in labels
            ),
            relations=(f"{labels[0]} and !{labels[1]} => {labels[2]}",),
        )
        before = source.model_dump_json()
        corrupted = corrupt_dictionary(source, seed=index)
        random_control = random_symbol_control(
            source,
            seed=index,
            tokenizer=tokenizer,
        )
        swapped = swap_labels(
            source,
            new_labels=tuple(f"Q{index * 3 + offset + 1}" for offset in range(3)),
        )
        restored = swap_labels(swapped.representation, new_labels=labels)

        assert all(
            corrupted.representation.definition_map()[label] != source.definition_map()[label]
            for label in labels
        )
        assert len(random_control.representation.symbols) == len(labels)
        assert restored.representation == source
        assert source.model_dump_json() == before
