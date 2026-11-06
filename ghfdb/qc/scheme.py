"""The concepts the quality scheme names, and the fields it scores read once."""

import math
from collections.abc import Iterable

import pandas
from frictionless import Schema

from ghfdb.fields import MissingSchemeError, Vocabularies, allowed_values
from ghfdb.qc.rules import (
    BOREHOLE,
    EXPLORATION_METHOD,
    PROBE_SENSING,
    VOCABULARIES,
)

HEAT_FLOW_CORRECTIONS = f"{VOCABULARIES}/heat-flow-corrections"
PRESENT_CORRECTED = f"{HEAT_FLOW_CORRECTIONS}/present_corrected"
PRESENT_NOT_CORRECTED = f"{HEAT_FLOW_CORRECTIONS}/present_not_corrected"
PRESENT_NOT_SIGNIFICANT = f"{HEAT_FLOW_CORRECTIONS}/present_not_significant"
NOT_RECOGNIZED = f"{HEAT_FLOW_CORRECTIONS}/not_recognized"
UNSPECIFIED_CORRECTION = f"{HEAT_FLOW_CORRECTIONS}/unspecified"

# The correction fields in the order of the perturbation flags S E T P V C R.
FLAG_FIELDS = ("C13", "C14", "C15", "C16", "C17", "C18", "C19")
CORRECTIONS = (
    PRESENT_CORRECTED,
    PRESENT_NOT_CORRECTED,
    PRESENT_NOT_SIGNIFICANT,
    NOT_RECOGNIZED,
    UNSPECIFIED_CORRECTION,
)

NUMBER_FIELDS = ("C1", "C2")
TERM_FIELDS = (EXPLORATION_METHOD, *FLAG_FIELDS)

# Every concept the scheme names, by the code of the field that must allow it.
CONCEPTS: tuple[tuple[str, str], ...] = (
    *((EXPLORATION_METHOD, uri) for uri in BOREHOLE.concepts + PROBE_SENSING.concepts),
    *((code, uri) for code in FLAG_FIELDS for uri in CORRECTIONS),
)


class Terms:
    """The concepts of the scheme resolved to the terms of the published vocabularies.

    Args:
        schema: The fields, which say where each takes its allowed values from.
        vocabularies: Where the allowed values come from. Without it, the vocabularies
            in the user's cache, downloaded when missing.
        concepts: The field code and concept URI of every concept to resolve.

    Attributes:
        allowed: The term of every allowed value that has a concept URI, by field
            code and then URI, for each field the scheme scores.
        concepts: The term of each concept the scheme names, by field code and URI.

    Raises:
        MissingSchemeError: A concept is not an allowed value of its field, or the
            field is not in the schema. The message names the field and the concept.
    """

    def __init__(
        self,
        schema: Schema,
        vocabularies: Vocabularies | None = None,
        concepts: Iterable[tuple[str, str]] = CONCEPTS,
    ) -> None:
        files = Vocabularies() if vocabularies is None else vocabularies
        pairs = tuple(concepts)
        fields = dict.fromkeys((*TERM_FIELDS, *(code for code, _ in pairs)))
        self.allowed = {code: self.read(schema, code, files) for code in fields}
        self.concepts: dict[tuple[str, str], str] = {}
        for code, uri in pairs:
            if uri not in self.allowed[code]:
                raise MissingSchemeError(f"{code}: {uri} is not an allowed value")
            self.concepts[code, uri] = self.allowed[code][uri]

    @staticmethod
    def read(schema: Schema, code: str, vocabularies: Vocabularies) -> dict[str, str]:
        """Map the concept URI of each allowed value of a field to its term.

        Args:
            schema: The fields.
            code: The field's code.
            vocabularies: Where the allowed values come from.

        Returns:
            The term of each allowed value that has a concept URI, empty for a field
            that is not in the schema.
        """
        if not any(field.name == code for field in schema.fields):
            return {}
        field = schema.get_field(code)
        return {
            value.uri: value.term
            for value in allowed_values(field, vocabularies)
            if value.uri
        }

    def term(self, code: str, uri: str) -> str:
        """Give the term a field accepts for a concept.

        Args:
            code: The field's code.
            uri: The concept's URI.

        Returns:
            The term, as it is written in the field.
        """
        return self.concepts[code, uri]

    def uris(self, code: str) -> dict[str, str]:
        """Map each term a field accepts to the URI of its concept.

        Args:
            code: The field's code.

        Returns:
            The URI of each term of the field that has one.
        """
        return {term: uri for uri, term in self.allowed.get(code, {}).items()}


class Inputs:
    """The fields the scheme scores, parsed once from a dataset.

    A cell that holds a Python list holds several values, in any scored field. Every
    value is a row of its own under the child's index. Text is never split.

    Args:
        data: One row per child and one column per field, named by field code.
        terms: The terms each vocabulary field accepts.

    Attributes:
        index: The index of the children.
        numbers: The numbers of each number field as floats, empty where the cell is
            empty, is not a number or is infinite.
        concepts: The concept URI of each vocabulary field's terms, empty where the
            cell is empty or holds a term the field does not allow.
    """

    def __init__(self, data: pandas.DataFrame, terms: Terms) -> None:
        self.index = data.index
        self.numbers = {
            code: self.number(self.values(data, code)) for code in NUMBER_FIELDS
        }
        self.concepts = {
            code: self.values(data, code).map(terms.uris(code)).astype("string")
            for code in TERM_FIELDS
        }

    @staticmethod
    def values(data: pandas.DataFrame, code: str) -> pandas.Series:
        """Read a field as stripped text, one row for each value.

        Args:
            data: The children.
            code: The field's code.

        Returns:
            The text of every value, empty for a field the data lacks.
        """
        if code not in data.columns:
            return pandas.Series(pandas.NA, index=data.index, dtype="string")
        return data[code].explode().astype("string").str.strip()

    @staticmethod
    def number(text: pandas.Series) -> pandas.Series:
        """Parse text as the check parses a number field.

        Args:
            text: Stripped text.

        Returns:
            The numbers as floats, NaN for what is not a number or is infinite.
        """
        numbers = pandas.to_numeric(text, errors="coerce").astype("float64")
        return numbers.where(numbers.abs() != math.inf)

    def first(self, values: pandas.Series) -> pandas.Series:
        """Keep one value for each child: its first filled one.

        Args:
            values: A parsed field, with a row for each value.

        Returns:
            The value of each child in the order of the children, empty for a child
            with no filled value.
        """
        return values.groupby(level=0, sort=False).first().reindex(self.index)
