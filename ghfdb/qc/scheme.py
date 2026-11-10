"""The concepts the quality scheme names, and the fields it scores read once."""

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Self

import numpy
import pandas
from frictionless import Schema

from ghfdb.fields import MissingSchemeError, Vocabularies, allowed_values
from ghfdb.qc import concepts as c
from ghfdb.qc.rules import BOREHOLE, EXPLORATION_METHOD, PROBE_SENSING

LARGEST_PENALTY = -0.2
DECIMALS = 3

CONSIDERED_P_OR_T = (c.CONSIDERED_P, c.CONSIDERED_T)
NOT_CONSIDERED_OR_UNSPECIFIED = (c.NOT_CONSIDERED, c.UNSPECIFIED_CORRECTION)
IN_SITU_CORRECTIONS = (
    c.CONSIDERED_PT,
    *CONSIDERED_P_OR_T,
    *NOT_CONSIDERED_OR_UNSPECIFIED,
)

CONTINUOUS_LOG_BEST = (c.LOG_EQ, c.C_LOG, c.DTS_EQ, c.C_DTS)
CONTINUOUS_LOG_PERTURBED = (c.LOG_PERT,)
CONTINUOUS_LOG_METHODS = (*CONTINUOUS_LOG_BEST, *CONTINUOUS_LOG_PERTURBED)
SINGLE_POINTS_EQUILIBRIUM = (
    c.LOG_EQ,
    c.C_LOG,
    c.C_BHT,
    c.HT_FT,
    c.C_HT_FT,
    c.RTD_EQ,
    c.C_RTD,
    c.ODTT_PC,
    c.ODTT_TP,
    c.EGRT,
    c.GRT,
    c.C_DTS,
)
SINGLE_POINTS_PERTURBED = (
    c.LOG_PERT,
    c.DTS_PERT,
    c.BHT,
    c.HT_FT_PERT,
    c.RTD_PERT,
    c.BLK,
)
ESTIMATED_TEMPERATURE = (
    c.CPD,
    c.XEN,
    c.GTM,
    c.BSR,
    c.UNSPECIFIED_TEMPERATURE,
    c.OTHER_TEMPERATURE,
)
SURFACE_BOTTOM_CORRECTED = (
    c.C_BHT,
    c.RTD_EQ,
    c.C_RTD,
    c.ODTT_PC,
    c.ODTT_TP,
    c.C_HT_FT,
    c.EGRT,
    c.GRT,
)
SURFACE_BOTTOM_PERTURBED = (c.BHT, c.HT_FT_PERT, c.RTD_PERT)
TEMPERATURE_METHOD_CONCEPTS = tuple(
    dict.fromkeys(
        (
            c.SURFACE,
            *CONTINUOUS_LOG_METHODS,
            *SINGLE_POINTS_EQUILIBRIUM,
            *SINGLE_POINTS_PERTURBED,
            *ESTIMATED_TEMPERATURE,
            *SURFACE_BOTTOM_CORRECTED,
            *SURFACE_BOTTOM_PERTURBED,
        )
    )
)

LOCATIONS = (c.ACTUAL_LOCATION, c.OTHER_LOCATION, c.LITERATURE_OR_UNSPECIFIED)

BEST_SOURCES = (c.IN_SITU_PROBE, c.CORE_LOG)
SAMPLED_SOURCES = (c.CUTTING_SAMPLES, c.OUTCROP_SAMPLES, c.WELL_LOG)
ESTIMATED_SOURCES = (
    c.MINERAL_COMPUTATION,
    c.UNSPECIFIED_SOURCE,
    c.OTHER_SOURCE,
    c.ASSUMED_FROM_LITERATURE,
)
SOURCE_CONCEPTS = (
    *BEST_SOURCES,
    c.CORE_SAMPLES,
    *SAMPLED_SOURCES,
    *ESTIMATED_SOURCES,
)

LABORATORY_METHODS = (
    c.POINT_SOURCE,
    c.LINE_SOURCE_FULL,
    c.LINE_SOURCE_HALF,
    c.PLANE_SOURCE_FULL,
    c.PLANE_SOURCE_HALF,
    c.LABORATORY_OTHER,
)
ESTIMATED_FROM_LITERATURE = (
    c.LITHOLOGY,
    c.WELL_LOG_DETERMINISTIC,
    c.WELL_LOG_EMPIRICAL,
)
ESTIMATED_FROM_OTHER = (
    c.WATER_CONTENT,
    c.MINERAL_COMPOSITION,
    c.CHLORINE_CONTENT,
    c.UNSPECIFIED_METHOD,
)
CONDUCTIVITY_METHOD_CONCEPTS = (
    c.PROBE_PULSE,
    *LABORATORY_METHODS,
    *ESTIMATED_FROM_LITERATURE,
    *ESTIMATED_FROM_OTHER,
)

DRY_UNSPECIFIED_OR_OTHER = (
    c.DRY_MEASURED,
    c.UNSPECIFIED_SATURATION,
    c.OTHER_SATURATION,
)
SATURATION_CONCEPTS = (
    c.SATURATED_IN_SITU,
    c.SATURATED_MEASURED,
    c.RECOVERED,
    c.SATURATED_CALCULATED,
    *DRY_UNSPECIFIED_OR_OTHER,
)

FULL_IN_SITU = (c.REPLICATED_PT, c.CORRECTED_PT)
PARTIAL_IN_SITU = (c.REPLICATED_P, c.CORRECTED_P, c.REPLICATED_T, c.CORRECTED_T)
AMBIENT_OR_UNSPECIFIED = (
    c.RECORDED_AMBIENT,
    c.UNRECORDED_AMBIENT,
    c.UNSPECIFIED_CONDITIONS,
)
CONDITIONS_CONCEPTS = (
    c.ACTUAL_IN_SITU,
    *FULL_IN_SITU,
    *PARTIAL_IN_SITU,
    *AMBIENT_OR_UNSPECIFIED,
)

# The correction fields in the order of the perturbation flags S E T P V C R.
FLAG_FIELDS = ("C13", "C14", "C15", "C16", "C17", "C18", "C19")
CORRECTIONS = (
    c.PRESENT_CORRECTED,
    c.PRESENT_NOT_CORRECTED,
    c.PRESENT_NOT_SIGNIFICANT,
    c.NOT_RECOGNIZED,
    c.UNSPECIFIED_CORRECTION,
)

NUMBER_FIELDS = ("C1", "C2", "P6", "C4", "C5", "C6", "C23", "C37", "C47")
TERM_FIELDS = (
    EXPLORATION_METHOD,
    *FLAG_FIELDS,
    "C11",
    "C12",
    "C31",
    "C32",
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
    *(("C11", uri) for uri in IN_SITU_CORRECTIONS),
    ("C12", c.TILT_CORRECTED),
    *(("C31", uri) for uri in TEMPERATURE_METHOD_CONCEPTS),
    *(("C32", uri) for uri in TEMPERATURE_METHOD_CONCEPTS),
    *(("C41", uri) for uri in SOURCE_CONCEPTS),
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

    @classmethod
    def poorest(
        cls, penalty: pandas.Series, marked: pandas.Series, index: pandas.Index
    ) -> Self:
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
        return cls(
            penalty.groupby(level=0, sort=False).min().reindex(index),
            chosen.groupby(level=0, sort=False).any().reindex(index),
        )

    @classmethod
    def cases(
        cls,
        rows: pandas.DataFrame,
        options: Sequence[tuple[float, pandas.Series]],
        index: pandas.Index,
    ) -> Self:
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
                numpy.where(
                    holds.fillna(False).to_numpy(dtype=bool), penalty, numpy.inf
                )
                for penalty, holds in options
            ]
        ).min(axis=1)
        empty = rows.isna().any(axis=1)
        penalty = pandas.Series(
            numpy.where(numpy.isinf(penalties) | empty, LARGEST_PENALTY, penalties),
            index=rows.index,
        )
        return cls.poorest(penalty, empty, index)

    @classmethod
    def bands(
        cls,
        numbers: pandas.Series,
        edges: Sequence[tuple[float, float]],
        index: pandas.Index,
        penalty_below: float = LARGEST_PENALTY,
    ) -> Self:
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
        return cls.poorest(penalty, numbers.isna(), index)


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

    @classmethod
    def total(cls, criteria: Sequence[Penalty], routed: pandas.Series) -> Self:
        """Add the penalties of the criteria to 1.0 for the children the rules score.

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
        marked = pandas.concat(
            [criterion.marked for criterion in criteria], axis=1
        ).any(axis=1)
        return cls(
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
