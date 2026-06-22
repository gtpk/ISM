from __future__ import annotations

import re
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

LABEL_TEXT = r"[A-Z][A-Z0-9_]*[0-9][A-Z0-9_]*"
LABEL_PATTERN = re.compile(rf"^{LABEL_TEXT}$")
LABEL_REFERENCE_PATTERN = re.compile(rf"(?<![A-Za-z0-9_])!?({LABEL_TEXT})(?![A-Za-z0-9_])")


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SymbolDefinition(FrozenModel):
    label: Annotated[str, Field(min_length=1)]
    definition: Annotated[str, Field(min_length=1)]

    @model_validator(mode="after")
    def validate_content(self) -> SymbolDefinition:
        if LABEL_PATTERN.fullmatch(self.label) is None:
            raise ValueError(f"invalid symbol label: {self.label}")
        if not self.definition.strip():
            raise ValueError("symbol definition must not be blank")
        return self


class ISMRepresentation(FrozenModel):
    symbols: Annotated[tuple[str, ...], Field(min_length=1)]
    dictionary: tuple[SymbolDefinition, ...]
    relations: tuple[str, ...]

    @model_validator(mode="after")
    def validate_structure(self) -> ISMRepresentation:
        if len(self.symbols) != len(set(self.symbols)):
            raise ValueError("symbol labels must be unique")
        invalid = [label for label in self.symbols if LABEL_PATTERN.fullmatch(label) is None]
        if invalid:
            raise ValueError(f"invalid symbol labels: {', '.join(invalid)}")

        dictionary_labels = [item.label for item in self.dictionary]
        if len(dictionary_labels) != len(set(dictionary_labels)):
            raise ValueError("dictionary labels must be unique")
        unknown_dictionary = set(dictionary_labels) - set(self.symbols)
        if unknown_dictionary:
            raise ValueError(
                f"dictionary contains undefined symbols: {', '.join(sorted(unknown_dictionary))}"
            )

        blank_relations = [relation for relation in self.relations if not relation.strip()]
        if blank_relations:
            raise ValueError("relations must not contain blank entries")
        unknown_references = self.referenced_labels() - set(self.symbols)
        if unknown_references:
            raise ValueError(
                f"relations reference undefined symbols: {', '.join(sorted(unknown_references))}"
            )
        return self

    def referenced_labels(self) -> set[str]:
        return {
            match.group(1)
            for relation in self.relations
            for match in LABEL_REFERENCE_PATTERN.finditer(relation)
        }

    def definition_map(self) -> dict[str, str]:
        return {item.label: item.definition for item in self.dictionary}
