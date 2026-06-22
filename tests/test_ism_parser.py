from __future__ import annotations

import pytest

from ism.representation.models import ISMRepresentation, SymbolDefinition
from ism.representation.parser import (
    ISMParseError,
    ParseErrorCode,
    parse_ism,
    serialize_ism,
)
from ism.representation.tokenizer import WhitespaceTokenCounter

VALID_ISM = """[DICTIONARY]
Z1 := marker_a high and marker_b low implies high risk
Z2 := repair score above threshold cancels escalation

[RELATIONS]
Z1 and not Z2 => HIGH
"""


class CharacterTokenCounter:
    def count(self, text: str) -> int:
        return len(text)


def test_p2_con_001_parser_serializer_round_trip() -> None:
    parsed = parse_ism(
        VALID_ISM,
        budget=100,
        tokenizer=WhitespaceTokenCounter(),
    )

    restored = parse_ism(
        serialize_ism(parsed),
        budget=100,
        tokenizer=WhitespaceTokenCounter(),
    )

    assert restored == parsed


def test_p2_con_002_duplicate_label_is_rejected() -> None:
    raw = """[DICTIONARY]
Z1 := first
Z1 := second

[RELATIONS]
Z1
"""

    with pytest.raises(ISMParseError) as captured:
        parse_ism(raw, budget=100, tokenizer=WhitespaceTokenCounter())

    assert captured.value.code is ParseErrorCode.INVALID_REPRESENTATION
    assert "dictionary labels must be unique" in str(captured.value)


def test_p2_con_003_undefined_reference_is_rejected() -> None:
    raw = """[DICTIONARY]
Z1 := first

[RELATIONS]
Z1 and Z9
"""

    with pytest.raises(ISMParseError) as captured:
        parse_ism(raw, budget=100, tokenizer=WhitespaceTokenCounter())

    assert captured.value.code is ParseErrorCode.INVALID_REPRESENTATION
    assert "Z9" in str(captured.value)


def test_p2_con_004_empty_sections_follow_condition_contract() -> None:
    symbol_only = """[DICTIONARY]

[RELATIONS]
Z1 => HIGH
"""
    parsed = parse_ism(
        symbol_only,
        budget=100,
        tokenizer=WhitespaceTokenCounter(),
        allow_empty_dictionary=True,
    )

    assert parsed.dictionary == ()
    assert parsed.symbols == ("Z1",)

    with pytest.raises(ISMParseError) as dictionary_error:
        parse_ism(symbol_only, budget=100, tokenizer=WhitespaceTokenCounter())
    assert dictionary_error.value.code is ParseErrorCode.EMPTY_DICTIONARY

    empty_relations = """[DICTIONARY]
Z1 := first

[RELATIONS]
"""
    with pytest.raises(ISMParseError) as relation_error:
        parse_ism(empty_relations, budget=100, tokenizer=WhitespaceTokenCounter())
    assert relation_error.value.code is ParseErrorCode.EMPTY_RELATIONS

    allowed = parse_ism(
        empty_relations,
        budget=100,
        tokenizer=WhitespaceTokenCounter(),
        allow_empty_relations=True,
    )
    assert allowed.relations == ()


@pytest.mark.parametrize(
    ("token_count", "budget", "accepted"),
    [(63, 64, True), (64, 64, True), (65, 64, False)],
)
def test_p2_fun_001_budget_boundary(
    token_count: int,
    budget: int,
    accepted: bool,
) -> None:
    definition = " ".join("word" for _ in range(token_count - 5))
    raw = f"[DICTIONARY]\nZ1 := {definition}\n\n[RELATIONS]\nZ1\n"
    assert WhitespaceTokenCounter().count(raw) == token_count

    if accepted:
        assert parse_ism(raw, budget=budget, tokenizer=WhitespaceTokenCounter())
    else:
        with pytest.raises(ISMParseError) as captured:
            parse_ism(raw, budget=budget, tokenizer=WhitespaceTokenCounter())
        assert captured.value.code is ParseErrorCode.BUDGET_EXCEEDED


def test_p2_fun_002_unicode_uses_tokenizer_count_not_character_assumption() -> None:
    raw = "[DICTIONARY]\nZ1 := 한글\n\n[RELATIONS]\nZ1\n"
    exact_budget = len(raw)

    assert parse_ism(raw, budget=exact_budget, tokenizer=CharacterTokenCounter())
    with pytest.raises(ISMParseError) as captured:
        parse_ism(raw, budget=exact_budget - 1, tokenizer=CharacterTokenCounter())
    assert captured.value.code is ParseErrorCode.BUDGET_EXCEEDED


def test_p2_err_001_malformed_output_preserves_raw_text_and_error_code() -> None:
    raw = "[DICTIONARY]\nthis is malformed\n[RELATIONS]\nZ1"

    with pytest.raises(ISMParseError) as captured:
        parse_ism(raw, budget=100, tokenizer=WhitespaceTokenCounter())

    assert captured.value.code is ParseErrorCode.MALFORMED_DICTIONARY
    assert captured.value.raw_output == raw
    assert captured.value.line_number == 2


def test_p2_err_002_parser_rejects_question_or_answer_leakage() -> None:
    raw = """[DICTIONARY]
Z1 := the answer is HIGH

[RELATIONS]
Z1
"""

    with pytest.raises(ISMParseError) as captured:
        parse_ism(
            raw,
            budget=100,
            tokenizer=WhitespaceTokenCounter(),
            questions=("What is the risk?",),
            answers=("HIGH",),
        )

    assert captured.value.code is ParseErrorCode.LEAKAGE_DETECTED
    assert captured.value.raw_output == raw


def test_p2_reg_001_rejects_unknown_and_duplicate_sections() -> None:
    unknown = "[NOTES]\nhello"
    duplicate = "[DICTIONARY]\nZ1 := one\n[DICTIONARY]\nZ2 := two\n[RELATIONS]\nZ1"

    with pytest.raises(ISMParseError) as unknown_error:
        parse_ism(unknown, budget=100, tokenizer=WhitespaceTokenCounter())
    with pytest.raises(ISMParseError) as duplicate_error:
        parse_ism(duplicate, budget=100, tokenizer=WhitespaceTokenCounter())

    assert unknown_error.value.code is ParseErrorCode.UNKNOWN_SECTION
    assert duplicate_error.value.code is ParseErrorCode.DUPLICATE_SECTION


def test_model_rejects_blank_definition() -> None:
    with pytest.raises(ValueError, match="definition"):
        SymbolDefinition(label="Z1", definition=" ")


def test_model_rejects_duplicate_symbols() -> None:
    with pytest.raises(ValueError, match="unique"):
        ISMRepresentation(symbols=("Z1", "Z1"), dictionary=(), relations=("Z1",))
