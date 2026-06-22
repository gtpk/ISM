from __future__ import annotations

import re
from enum import StrEnum

from pydantic import ValidationError

from ism.representation.leakage import find_leakage
from ism.representation.models import LABEL_TEXT, ISMRepresentation, SymbolDefinition
from ism.representation.tokenizer import TokenCounter

SECTION_PATTERN = re.compile(r"^\[([A-Z_]+)\]$")
DICTIONARY_LINE_PATTERN = re.compile(rf"^({LABEL_TEXT})\s*:=\s*(.+)$")


class ParseErrorCode(StrEnum):
    MALFORMED_SECTION = "malformed_section"
    UNKNOWN_SECTION = "unknown_section"
    DUPLICATE_SECTION = "duplicate_section"
    MALFORMED_DICTIONARY = "malformed_dictionary"
    EMPTY_DICTIONARY = "empty_dictionary"
    EMPTY_RELATIONS = "empty_relations"
    INVALID_REPRESENTATION = "invalid_representation"
    BUDGET_EXCEEDED = "budget_exceeded"
    LEAKAGE_DETECTED = "leakage_detected"


class ISMParseError(ValueError):
    def __init__(
        self,
        code: ParseErrorCode,
        message: str,
        *,
        raw_output: str,
        line_number: int | None = None,
    ) -> None:
        location = f" at line {line_number}" if line_number is not None else ""
        super().__init__(f"{code.value}{location}: {message}")
        self.code = code
        self.raw_output = raw_output
        self.line_number = line_number


def parse_ism(
    raw_output: str,
    *,
    budget: int,
    tokenizer: TokenCounter,
    allow_empty_dictionary: bool = False,
    allow_empty_relations: bool = False,
    questions: tuple[str, ...] = (),
    answers: tuple[str, ...] = (),
) -> ISMRepresentation:
    if budget < 1:
        raise ValueError("budget must be positive")
    token_count = tokenizer.count(raw_output)
    if token_count > budget:
        raise ISMParseError(
            ParseErrorCode.BUDGET_EXCEEDED,
            f"output uses {token_count} tokens, budget is {budget}",
            raw_output=raw_output,
        )
    leakage = find_leakage(raw_output, questions=questions, answers=answers)
    if leakage:
        sources = ", ".join(sorted({item.source for item in leakage}))
        raise ISMParseError(
            ParseErrorCode.LEAKAGE_DETECTED,
            f"output contains protected {sources} text",
            raw_output=raw_output,
        )

    sections: dict[str, list[tuple[int, str]]] = {}
    current: str | None = None
    for line_number, raw_line in enumerate(raw_output.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        section_match = SECTION_PATTERN.fullmatch(line)
        if section_match:
            section = section_match.group(1)
            if section not in {"DICTIONARY", "RELATIONS"}:
                raise ISMParseError(
                    ParseErrorCode.UNKNOWN_SECTION,
                    f"section [{section}] is not allowed",
                    raw_output=raw_output,
                    line_number=line_number,
                )
            if section in sections:
                raise ISMParseError(
                    ParseErrorCode.DUPLICATE_SECTION,
                    f"section [{section}] appears more than once",
                    raw_output=raw_output,
                    line_number=line_number,
                )
            sections[section] = []
            current = section
            continue
        if current is None:
            raise ISMParseError(
                ParseErrorCode.MALFORMED_SECTION,
                "content appears before a section header",
                raw_output=raw_output,
                line_number=line_number,
            )
        sections[current].append((line_number, line))

    dictionary_lines = sections.get("DICTIONARY", [])
    relation_lines = sections.get("RELATIONS", [])
    if not dictionary_lines and not allow_empty_dictionary:
        raise ISMParseError(
            ParseErrorCode.EMPTY_DICTIONARY,
            "dictionary must contain at least one definition",
            raw_output=raw_output,
        )
    if not relation_lines and not allow_empty_relations:
        raise ISMParseError(
            ParseErrorCode.EMPTY_RELATIONS,
            "relations must contain at least one entry",
            raw_output=raw_output,
        )

    definitions: list[SymbolDefinition] = []
    for line_number, line in dictionary_lines:
        match = DICTIONARY_LINE_PATTERN.fullmatch(line)
        if match is None:
            raise ISMParseError(
                ParseErrorCode.MALFORMED_DICTIONARY,
                "expected LABEL := non-empty definition",
                raw_output=raw_output,
                line_number=line_number,
            )
        definitions.append(SymbolDefinition(label=match.group(1), definition=match.group(2)))

    symbols = tuple(dict.fromkeys(item.label for item in definitions))
    if not symbols and relation_lines:
        symbols = tuple(
            dict.fromkeys(
                match.group(1)
                for _, relation in relation_lines
                for match in re.finditer(
                    rf"(?<![A-Za-z0-9_])!?({LABEL_TEXT})(?![A-Za-z0-9_])",
                    relation,
                )
            )
        )
    try:
        return ISMRepresentation(
            symbols=symbols,
            dictionary=tuple(definitions),
            relations=tuple(line for _, line in relation_lines),
        )
    except ValidationError as error:
        raise ISMParseError(
            ParseErrorCode.INVALID_REPRESENTATION,
            str(error),
            raw_output=raw_output,
        ) from error


def serialize_ism(representation: ISMRepresentation) -> str:
    lines = ["[DICTIONARY]"]
    lines.extend(f"{item.label} := {item.definition}" for item in representation.dictionary)
    lines.append("")
    lines.append("[RELATIONS]")
    lines.extend(representation.relations)
    return "\n".join(lines) + "\n"
