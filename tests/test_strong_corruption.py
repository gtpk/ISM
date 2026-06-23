from __future__ import annotations

from ism.experiments.diagnostics import flip_changes_content
from ism.representation.interventions import blank_dictionary, flip_conclusions
from ism.representation.models import ISMRepresentation, SymbolDefinition


def _rep() -> ISMRepresentation:
    return ISMRepresentation(
        symbols=("Z1", "Z2", "Z3"),
        dictionary=(
            SymbolDefinition(
                label="Z1",
                definition="if marker_a = high and marker_b = low then risk = HIGH",
            ),
            SymbolDefinition(label="Z2", definition="if repair_score >= 0.8 then risk = LOW"),
            SymbolDefinition(label="Z3", definition="if at least 2 then review = True"),
        ),
        relations=("Z1 Z2 !Z3",),
    )


def test_flip_inverts_conclusions_but_not_lowercase_conditions() -> None:
    flipped = {d.label: d.definition for d in flip_conclusions(_rep()).representation.dictionary}
    # conclusion HIGH -> LOW; condition tokens "high"/"low" stay lowercase.
    assert flipped["Z1"] == "if marker_a = high and marker_b = low then risk = LOW"
    assert flipped["Z2"].endswith("risk = HIGH")  # LOW -> HIGH
    assert "review = False" in flipped["Z3"]  # True -> False


def test_flip_preserves_relations_and_labels() -> None:
    flipped = flip_conclusions(_rep()).representation
    assert flipped.relations == _rep().relations
    assert flipped.symbols == _rep().symbols


def test_blank_dictionary_redacts_definitions_keeps_labels() -> None:
    blanked = blank_dictionary(_rep()).representation
    assert all(item.definition == "redacted" for item in blanked.dictionary)
    assert blanked.symbols == _rep().symbols
    assert blanked.relations == _rep().relations


def test_flip_changes_content_detects_conclusion_presence() -> None:
    assert flip_changes_content(_rep()) is True

    conditions_only = ISMRepresentation(
        symbols=("Z1", "Z2"),
        dictionary=(
            SymbolDefinition(label="Z1", definition="marker_a = high"),
            SymbolDefinition(label="Z2", definition="marker_b = low"),
        ),
        relations=("Z1 Z2",),
    )
    assert flip_changes_content(conditions_only) is False
