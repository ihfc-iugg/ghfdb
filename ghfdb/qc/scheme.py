"""The concepts the quality scheme names, and the fields it scores read once."""

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import numpy
import pandas
from frictionless import Schema

from ghfdb.fields import MissingSchemeError, Vocabularies, allowed_values
from ghfdb.qc.rules import (
    BOREHOLE,
    CONDUCTIVITY_LOCATION,
    CONDUCTIVITY_SOURCES,
    EXPLORATION_METHOD,
    LITERATURE_OR_UNSPECIFIED,
    PROBE_SENSING,
    VOCABULARIES,
)

LARGEST_PENALTY = -0.2
DECIMALS = 3

HEAT_FLOW_CORRECTIONS = f"{VOCABULARIES}/heat-flow-corrections"
PRESENT_CORRECTED = f"{HEAT_FLOW_CORRECTIONS}/present_corrected"
PRESENT_NOT_CORRECTED = f"{HEAT_FLOW_CORRECTIONS}/present_not_corrected"
PRESENT_NOT_SIGNIFICANT = f"{HEAT_FLOW_CORRECTIONS}/present_not_significant"
NOT_RECOGNIZED = f"{HEAT_FLOW_CORRECTIONS}/not_recognized"
UNSPECIFIED_CORRECTION = f"{HEAT_FLOW_CORRECTIONS}/unspecified"
TILT_CORRECTED = f"{HEAT_FLOW_CORRECTIONS}/tiltCorrected"

ACTUAL_LOCATION = f"{CONDUCTIVITY_LOCATION}/actual"
OTHER_LOCATION = f"{CONDUCTIVITY_LOCATION}/other"
LOCATIONS = (ACTUAL_LOCATION, OTHER_LOCATION, LITERATURE_OR_UNSPECIFIED)

IN_SITU_PROBE = f"{CONDUCTIVITY_SOURCES}/insitu_probe"

CONDUCTIVITY_METHODS = f"{VOCABULARIES}/conductivity-methods"
PROBE_PULSE = f"{CONDUCTIVITY_METHODS}/probePulse"
LABORATORY_METHODS = tuple(
    f"{CONDUCTIVITY_METHODS}/{name}"
    for name in (
        "pointSource",
        "lineSourceFull",
        "lineSourceHalf",
        "planeSourceFull",
        "planeSourceHalf",
        "laboratoryOther",
    )
)
ESTIMATED_FROM_LITERATURE = tuple(
    f"{CONDUCTIVITY_METHODS}/{name}"
    for name in ("lithology", "wellLogDeterministic", "wellLogEmpirical")
)
ESTIMATED_FROM_OTHER = tuple(
    f"{CONDUCTIVITY_METHODS}/{name}"
    for name in ("waterContent", "mineralComposition", "chlorineContent", "unspecified")
)
CONDUCTIVITY_METHOD_CONCEPTS = (
    PROBE_PULSE,
    *LABORATORY_METHODS,
    *ESTIMATED_FROM_LITERATURE,
    *ESTIMATED_FROM_OTHER,
)

CONDUCTIVITY_SATURATION = f"{VOCABULARIES}/conductivity-saturation"
SATURATED_IN_SITU = f"{CONDUCTIVITY_SATURATION}/saturatedInSitu"
SATURATED_MEASURED = f"{CONDUCTIVITY_SATURATION}/saturatedMeasured"
RECOVERED = f"{CONDUCTIVITY_SATURATION}/recovered"
SATURATED_CALCULATED = f"{CONDUCTIVITY_SATURATION}/saturatedCalculated"
DRY_UNSPECIFIED_OR_OTHER = tuple(
    f"{CONDUCTIVITY_SATURATION}/{name}"
    for name in ("dryMeasured", "unspecified", "other")
)
SATURATION_CONCEPTS = (
    SATURATED_IN_SITU,
    SATURATED_MEASURED,
    RECOVERED,
    SATURATED_CALCULATED,
    *DRY_UNSPECIFIED_OR_OTHER,
)

CONDUCTIVITY_CONDITIONS = f"{VOCABULARIES}/conductivity-conditions"
ACTUAL_IN_SITU = f"{CONDUCTIVITY_CONDITIONS}/actualInSitu"
FULL_IN_SITU = tuple(
    f"{CONDUCTIVITY_CONDITIONS}/{name}" for name in ("replicatedPT", "correctedPT")
)
PARTIAL_IN_SITU = tuple(
    f"{CONDUCTIVITY_CONDITIONS}/{name}"
    for name in (
        "replicatedP",
        "correctedP",
        "replicatedT",
        "correctedT",
    )
)
AMBIENT_OR_UNSPECIFIED = tuple(
    f"{CONDUCTIVITY_CONDITIONS}/{name}"
    for name in ("recordedAmbient", "unrecordedAmbient", "unspecified")
)
CONDITIONS_CONCEPTS = (
    ACTUAL_IN_SITU,
    *FULL_IN_SITU,
    *PARTIAL_IN_SITU,
    *AMBIENT_OR_UNSPECIFIED,
)

# The correction fields in the order of the perturbation flags S E T P V C R.
FLAG_FIELDS = ("C13", "C14", "C15", "C16", "C17", "C18", "C19")
CORRECTIONS = (
    PRESENT_CORRECTED,
    PRESENT_NOT_CORRECTED,
    PRESENT_NOT_SIGNIFICANT,
    NOT_RECOGNIZED,
    UNSPECIFIED_CORRECTION,
)

NUMBER_FIELDS = ("C1", "C2", "P6", "C6", "C23", "C37", "C47")
TERM_FIELDS = (
    EXPLORATION_METHOD,
    *FLAG_FIELDS,
    "C12",
    "C41",
    "C42",
    "C43",
    "C44",
    "C45",
)

# Every concept the scheme names, by the code of the field that must allow it.
CONCEPTS: tuple[tuple[str, str], ...] = (
    *((EXPLORATION_METHOD, uri) for uri in BOREHOLE.concepts + PROBE_SENSING.concepts),
    *((code, uri) for code in FLAG_FIELDS for uri in CORRECTIONS),
    ("C12", TILT_CORRECTED),
    ("C41", IN_SITU_PROBE),
    *(("C42", uri) for uri in LOCATIONS),
    *(("C43", uri) for uri in CONDUCTIVITY_METHOD_CONCEPTS),
    *(("C44", uri) for uri in SATURATION_CONCEPTS),
    *(("C45", uri) for uri in CONDITIONS_CONCEPTS),
)


@dataclass(frozen=True)
class Penalty:
    """What one criterion adds to a score, for every child.

    Attributes:
        value: The penalty of each child, in the order of the children.
        marked: Whether the criterion sets the missing-information mark for each child.
    """

    value: pandas.Series
    marked: pandas.Series


@dataclass(frozen=True)
class Score:
    """A T-score or a TC-score, for every child.

    Attributes:
        value: The score of each child, in the order of the children, ``<NA>`` for a
            child the rules do not score.
        marked: Whether the score carries the missing-information mark, ``<NA>`` where
            the score is.
    """

    value: pandas.Series
    marked: pandas.Series


def poorest(
    penalty: pandas.Series, marked: pandas.Series, index: pandas.Index
) -> Penalty:
    """Keep the poorest of the values of each child.

    Args:
        penalty: The penalty of every value, under the index of its child.
        marked: Whether each value sets the mark.
        index: The index of the children.

    Returns:
        The lowest penalty of each child, marked when a value with that penalty is.
    """
    lowest = penalty.groupby(level=0, sort=False).transform("min")
    chosen = marked & (penalty == lowest)
    return Penalty(
        penalty.groupby(level=0, sort=False).min().reindex(index),
        chosen.groupby(level=0, sort=False).any().reindex(index),
    )


def combinations(fields: dict[str, pandas.Series]) -> pandas.DataFrame:
    """Pair every value of each field with every value of the others, per child.

    Args:
        fields: The parsed values of each field, with a row for each value, by the
            name the combination gives it.

    Returns:
        One row for each combination, under the index of its child.
    """
    names = iter(fields)
    first = next(names)
    rows = fields[first].rename(first).to_frame()
    for name in names:
        rows = rows.join(fields[name].rename(name))
    return rows


def cases(
    rows: pandas.DataFrame,
    options: Sequence[tuple[float, pandas.Series]],
    index: pandas.Index,
) -> Penalty:
    """Score a list of cases: the poorest case that holds counts.

    Args:
        rows: The combinations of values.
        options: The penalty of each case and whether it holds in each row.
        index: The index of the children.

    Returns:
        The poorest penalty of each child: ``-0.2`` with the mark when a field
        of the rows is empty, and ``-0.2`` without it when no case holds.
    """
    penalties = numpy.column_stack(
        [
            numpy.where(holds.fillna(False).to_numpy(dtype=bool), penalty, numpy.inf)
            for penalty, holds in options
        ]
    ).min(axis=1)
    empty = rows.isna().any(axis=1)
    penalty = pandas.Series(
        numpy.where(numpy.isinf(penalties) | empty, LARGEST_PENALTY, penalties),
        index=rows.index,
    )
    return poorest(penalty, empty, index)


def bands(
    numbers: pandas.Series,
    edges: Sequence[tuple[float, float]],
    index: pandas.Index,
    penalty_below: float = LARGEST_PENALTY,
) -> Penalty:
    """Score numbers in bands that are open at the lower end.

    Args:
        numbers: The parsed values of a field.
        edges: A lower edge and the penalty of a number above it, largest first.
        index: The index of the children.
        penalty_below: The penalty of a number at or below every edge.

    Returns:
        The poorest penalty of each child, with the mark where the number is empty.
    """
    conditions = [numbers > edge for edge, _ in edges]
    choices = [penalty for _, penalty in edges]
    penalty = pandas.Series(
        numpy.select(conditions, choices, penalty_below), index=numbers.index
    )
    return poorest(penalty, numbers.isna(), index)


def total(criteria: Sequence[Penalty], routed: pandas.Series) -> Score:
    """Add the penalties of the criteria to 1.0 for the children a set of rules scores.

    Args:
        criteria: The penalty of each criterion.
        routed: Whether the rules score each child.

    Returns:
        The score rounded to three places and whether any criterion sets the mark,
        ``<NA>`` for a child the rules do not score.
    """
    value = sum(
        (criterion.value for criterion in criteria),
        pandas.Series(1.0, index=routed.index),
    )
    marked = pandas.concat([criterion.marked for criterion in criteria], axis=1).any(
        axis=1
    )
    return Score(
        value.round(DECIMALS).astype("Float64").where(routed),
        marked.astype("boolean").where(routed),
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
            return pandas.Series(pandas.NA, index=data.index, dtype="string", name=code)
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
