"""Penalties, and the three kinds of table that give them.

A criterion of the quality scheme is a table that gives each value of a field, or each
combination of values of several fields, a penalty. There are three kinds:

* ``Bands``: a number against ordered edges.
* ``Classes``: a term against groups of concepts.
* ``Cases``: rows of conditions on several fields, the poorest row that holds counting.

Each table scores every child at once from ``Inputs``, keeps the poorest of a child's
values, and lists its rows as data so the documentation can render them.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol, Self

import numpy
import pandas

from ghfdb.fields import Field
from ghfdb.qc.inputs import Inputs

SCORE_DECIMALS = 3
Conditions = Mapping[Field, Sequence[str]]


@dataclass(frozen=True)
class Outcome:
    """What an input scores when it has no penalty of its own.

    Attributes:
        penalty: The penalty.
        marked: Whether the input sets the missing-information mark.
    """

    penalty: float
    marked: bool = False


LARGEST = Outcome(-0.2)
LARGEST_MARKED = Outcome(-0.2, marked=True)


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
        if penalty.index.is_unique:
            return cls(penalty.reindex(index), marked.reindex(index))
        lowest = penalty.groupby(level=0, sort=False).transform("min")
        chosen = marked & (penalty == lowest)
        return cls(
            penalty.groupby(level=0, sort=False).min().reindex(index),
            chosen.groupby(level=0, sort=False).any().reindex(index),
        )

    def waived(self, where: numpy.ndarray) -> Self:
        """Take away the penalty and the mark from some children.

        Args:
            where: Whether each child is waived, in the order of the children.

        Returns:
            The penalty, ``0`` without the mark for the children waived.
        """
        return type(self)(self.value.mask(where, 0.0), self.marked.mask(where, False))


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
    def total(cls, penalties: Sequence[Penalty], routed: numpy.ndarray) -> Self:
        """Add the penalties of the criteria to 1.0 for the children the rules score.

        Args:
            penalties: The penalty of each criterion.
            routed: Whether the rules score each child.

        Returns:
            The score rounded to three places and whether any criterion sets the mark,
            ``<NA>`` for a child the rules do not score.
        """
        index = penalties[0].value.index
        value = sum((p.value for p in penalties), pandas.Series(1.0, index=index))
        marked = pandas.concat([p.marked for p in penalties], axis=1).any(axis=1)
        return cls(
            value.round(SCORE_DECIMALS).astype("Float64").where(routed),
            marked.astype("boolean").where(routed),
        )


@dataclass(frozen=True)
class RuleScores:
    """The scores a set of rules gives every child.

    Attributes:
        t: The T-score, with the child's corrections applied.
        tc: The TC-score, with the child's corrections applied.
        own_t: The T-score of the gradient on its own, before the corrections apply.
        own_tc: The TC-score of the conductivity on its own.
    """

    t: Score
    tc: Score
    own_t: Score
    own_tc: Score


@dataclass(frozen=True)
class Band:
    """The numbers above an edge, which stand for one value.

    Attributes:
        value: What the band stands for: a penalty in a table, a class in a grade.
        above: The edge. The band holds the numbers above it, or every number when
            there is none.
        inclusive: Whether the edge itself is in the band.
    """

    value: float
    above: float | None = None
    inclusive: bool = False

    def holds(self, numbers: pandas.Series) -> numpy.ndarray:
        """Say which numbers are in the band.

        Args:
            numbers: The numbers.

        Returns:
            Whether each number is in the band, False for an empty one.
        """
        if self.above is None:
            return numpy.ones(len(numbers), dtype=bool)
        found = numbers >= self.above if self.inclusive else numbers > self.above
        return found.to_numpy(dtype=bool)

    @classmethod
    def select(
        cls, bands: Sequence[Self], numbers: pandas.Series, default: float
    ) -> numpy.ndarray:
        """Give each number the value of the first band that holds it.

        Args:
            bands: The bands, the highest first.
            numbers: The numbers.
            default: The value of a number no band holds.

        Returns:
            The value of each number.
        """
        return numpy.select(
            [band.holds(numbers) for band in bands],
            [band.value for band in bands],
            default,
        )


def combine(columns: Mapping[str, pandas.Series]) -> pandas.DataFrame:
    """Pair every value of each field with every value of the others, per child.

    Args:
        columns: The values of each field, one row for each value, by the name of the
            field.

    Returns:
        One row for each combination, under the index of its child.
    """
    names = iter(columns)
    first = next(names)
    rows = columns[first].rename(first).to_frame()
    for name in names:
        rows = rows.join(columns[name].rename(name))
    return rows


def hold_all(rows: pandas.DataFrame, conditions: Conditions) -> numpy.ndarray:
    """Say which rows satisfy every condition.

    Args:
        rows: The concepts of each field, one row for each combination of values.
        conditions: The concepts each named field may hold.

    Returns:
        Whether every condition holds in each row. A row holds every condition of an
        empty set.
    """
    holds = numpy.ones(len(rows), dtype=bool)
    for field, concepts in conditions.items():
        holds &= rows[field].isin(concepts).to_numpy(dtype=bool)
    return holds


def settle(
    index: pandas.Index,
    penalty: numpy.ndarray,
    matched: numpy.ndarray,
    empty_values: numpy.ndarray,
    empty: Outcome,
    unmatched: Outcome,
) -> tuple[pandas.Series, pandas.Series]:
    """Give every value its penalty, or the outcome of an empty or unmatched value.

    Args:
        index: The index of the values.
        penalty: The penalty of each value that matched.
        matched: Whether each value matched a row of the table.
        empty_values: Whether each value is empty. An empty value is never matched.
        empty: The outcome of an empty value.
        unmatched: The outcome of a value that matches no row.

    Returns:
        The penalty of each value and whether it sets the mark.
    """
    penalties = numpy.where(matched, penalty, unmatched.penalty)
    marks = ~matched & unmatched.marked
    penalties = numpy.where(empty_values, empty.penalty, penalties)
    marks = numpy.where(empty_values, empty.marked, marks)
    return pandas.Series(penalties, index=index), pandas.Series(marks, index=index)


class Table(Protocol):
    """What every kind of table offers."""

    def reads(self) -> tuple[str, ...]:
        """List the fields the table reads."""
        ...

    def concepts(self) -> tuple[tuple[str, str], ...]:
        """List the field and concept URI of every concept the table names."""
        ...

    def rows(self) -> Sequence[object]:
        """List the rows of the table, as data."""
        ...

    def score(self, inputs: Inputs) -> Penalty:
        """Give the penalty of every child."""
        ...


@dataclass(frozen=True)
class Bands:
    """A number field against ordered edges.

    The first band that holds a number gives its penalty. A number that is empty or not
    a number takes ``empty``, and one that no band holds takes ``unmatched``.

    Attributes:
        field: The number field.
        bands: The bands, the highest first.
        empty: The outcome of an empty number.
        unmatched: The outcome of a number no band holds.
        left_out_when: Conditions on other fields that leave the criterion out for a
            value: it then adds no penalty and no mark.
    """

    field: Field
    bands: tuple[Band, ...]
    empty: Outcome = LARGEST_MARKED
    unmatched: Outcome = LARGEST
    left_out_when: Conditions | None = None

    def reads(self) -> tuple[str, ...]:
        """List the number field, then the fields of ``left_out_when``."""
        return (self.field, *(self.left_out_when or ()))

    def concepts(self) -> tuple[tuple[str, str], ...]:
        """List the concepts of ``left_out_when``."""
        return tuple(
            (field, uri)
            for field, concepts in (self.left_out_when or {}).items()
            for uri in concepts
        )

    def rows(self) -> tuple[Band, ...]:
        """List the bands."""
        return self.bands

    def values(self, numbers: pandas.Series) -> tuple[pandas.Series, pandas.Series]:
        """Give each number its penalty.

        Args:
            numbers: The numbers, one row for each value.

        Returns:
            The penalty of each number and whether it sets the mark.
        """
        holds = [band.holds(numbers) for band in self.bands]
        return settle(
            numbers.index,
            numpy.select(holds, [band.value for band in self.bands], 0.0),
            numpy.any(holds, axis=0),
            numbers.isna().to_numpy(),
            self.empty,
            self.unmatched,
        )

    def score(self, inputs: Inputs) -> Penalty:
        """Score the number of every child.

        Args:
            inputs: The scored fields.

        Returns:
            The poorest penalty of each child.
        """
        numbers = inputs.numbers(self.field)
        if self.left_out_when is None:
            return Penalty.poorest(*self.values(numbers), inputs.index)
        rows = combine(
            {
                self.field: numbers,
                **{field: inputs.concepts(field) for field in self.left_out_when},
            }
        )
        penalty, marked = self.values(rows[self.field])
        left_out = hold_all(rows, self.left_out_when)
        return Penalty.poorest(
            penalty.mask(left_out, 0.0), marked.mask(left_out, False), inputs.index
        )


@dataclass(frozen=True)
class Group:
    """Concepts that share a penalty.

    Attributes:
        penalty: The penalty.
        concepts: The URIs of the concepts.
    """

    penalty: float
    concepts: tuple[str, ...]


@dataclass(frozen=True)
class Classes:
    """A term field against groups of concepts.

    A value takes the penalty of the group its concept is in. A value that is empty
    takes ``empty``, and one whose concept is in no group takes ``unmatched``.

    Attributes:
        fields: The fields read. Their values are scored together, and the poorest
            counts.
        groups: The groups.
        empty: The outcome of an empty value.
        unmatched: The outcome of a concept in no group.
        skip_empty: Whether an empty value is left out when the child holds another,
            as the temperature method at one end of an interval is when the other end
            has one.
    """

    fields: tuple[Field, ...]
    groups: tuple[Group, ...]
    empty: Outcome = LARGEST_MARKED
    unmatched: Outcome = LARGEST_MARKED
    skip_empty: bool = False

    def reads(self) -> tuple[str, ...]:
        """List the fields."""
        return self.fields

    def concepts(self) -> tuple[tuple[str, str], ...]:
        """List every concept of every group, for each field."""
        return tuple(
            (field, uri)
            for field in self.fields
            for group in self.groups
            for uri in group.concepts
        )

    def rows(self) -> tuple[Group, ...]:
        """List the groups."""
        return self.groups

    def membership(self, concepts: pandas.Series) -> list[numpy.ndarray]:
        """Say which concepts are in each group.

        Args:
            concepts: The concept of every value.

        Returns:
            For each group, whether each concept is in it.
        """
        return [
            concepts.isin(group.concepts).to_numpy(dtype=bool) for group in self.groups
        ]

    def fits(self, concepts: pandas.Series) -> numpy.ndarray:
        """Say which concepts are in a group.

        Args:
            concepts: The concept of every value.

        Returns:
            Whether each concept is in a group.
        """
        return numpy.any(self.membership(concepts), axis=0)

    def values(self, concepts: pandas.Series) -> tuple[pandas.Series, pandas.Series]:
        """Give each concept the penalty of its group.

        Args:
            concepts: The concept of every value.

        Returns:
            The penalty of each value and whether it sets the mark.
        """
        member = self.membership(concepts)
        return settle(
            concepts.index,
            numpy.select(member, [group.penalty for group in self.groups], 0.0),
            numpy.any(member, axis=0),
            concepts.isna().to_numpy(),
            self.empty,
            self.unmatched,
        )

    def score(self, inputs: Inputs) -> Penalty:
        """Score every value of the fields of every child.

        Args:
            inputs: The scored fields.

        Returns:
            The poorest penalty of each child.
        """
        concepts = pandas.concat([inputs.concepts(field) for field in self.fields])
        penalty, marked = self.values(concepts)
        if self.skip_empty:
            filled = concepts.notna()
            some_filled = filled.groupby(level=0, sort=False).transform("any")
            keep = (filled | ~some_filled).to_numpy()
            penalty, marked = penalty[keep], marked[keep]
        return Penalty.poorest(penalty, marked, inputs.index)


@dataclass(frozen=True)
class Case:
    """A row of a table of cases.

    Attributes:
        penalty: The penalty when the row holds.
        conditions: The concepts each named field must hold. A field the row does not
            name may hold anything.
        every: The concepts every value of each named field must be among, which only
            matters for a field that holds several values.
    """

    penalty: float
    conditions: Conditions
    every: Conditions | None = None

    def fields(self) -> tuple[Field, ...]:
        """List the fields the row names, in order of first mention."""
        return tuple(dict.fromkeys((*self.conditions, *(self.every or ()))))

    def concepts(self) -> tuple[tuple[Field, str], ...]:
        """List the concepts the row names, with their fields."""
        return tuple(
            (field, uri)
            for conditions in (self.conditions, self.every or {})
            for field, concepts in conditions.items()
            for uri in concepts
        )

    def holds(self, rows: pandas.DataFrame, inputs: Inputs) -> numpy.ndarray:
        """Say which combinations of values the row holds for.

        Args:
            rows: The concepts of each field, one row for each combination of values.
            inputs: The scored fields, from which every value of a child is read.

        Returns:
            Whether the row holds in each combination.
        """
        holds = hold_all(rows, self.conditions)
        for field, concepts in (self.every or {}).items():
            every = pandas.Series(
                inputs.every_value(inputs.concepts(field).isin(concepts)),
                index=inputs.index,
            )
            holds &= every.reindex(rows.index).to_numpy(dtype=bool)
        return holds


@dataclass(frozen=True)
class Cases:
    """Rows of conditions on several fields.

    Every row whose conditions all hold counts, and the poorest penalty wins. A
    combination with an empty field that any row names takes ``empty``, and one that no
    row holds takes ``unmatched``.

    Attributes:
        cases: The rows.
        empty: The outcome of an empty field.
        unmatched: The outcome of a combination no row holds.
    """

    cases: tuple[Case, ...]
    empty: Outcome = LARGEST_MARKED
    unmatched: Outcome = LARGEST

    def reads(self) -> tuple[str, ...]:
        """List the fields the rows name, in order of first mention."""
        return tuple(
            dict.fromkeys(field for case in self.cases for field in case.fields())
        )

    def concepts(self) -> tuple[tuple[str, str], ...]:
        """List the concepts of every row, with their fields, each once."""
        return tuple(
            dict.fromkeys(pair for case in self.cases for pair in case.concepts())
        )

    def rows(self) -> tuple[Case, ...]:
        """List the rows."""
        return self.cases

    def score(self, inputs: Inputs) -> Penalty:
        """Score every combination of the values of the fields of every child.

        Args:
            inputs: The scored fields.

        Returns:
            The poorest penalty of each child.
        """
        rows = combine({field: inputs.concepts(field) for field in self.reads()})
        penalties = numpy.column_stack(
            [
                numpy.where(case.holds(rows, inputs), case.penalty, numpy.inf)
                for case in self.cases
            ]
        ).min(axis=1)
        penalty, marked = settle(
            rows.index,
            penalties,
            numpy.isfinite(penalties),
            rows.isna().any(axis=1).to_numpy(),
            self.empty,
            self.unmatched,
        )
        return Penalty.poorest(penalty, marked, inputs.index)


@dataclass(frozen=True)
class Criterion[T: Table]:
    """One criterion of the quality scheme.

    Attributes:
        identifier: The criterion's identifier in the worked examples, such as
            ``probe-t.penetration``.
        title: What the criterion scores, in a few words.
        table: The table that gives the penalties.
        source: The paper's table and row the criterion comes from.
    """

    identifier: str
    title: str
    table: T
    source: str

    def reads(self) -> tuple[str, ...]:
        """List the fields the criterion reads."""
        return self.table.reads()

    def concepts(self) -> tuple[tuple[str, str], ...]:
        """List the concepts the criterion names, with their fields."""
        return self.table.concepts()

    def score(self, inputs: Inputs) -> Penalty:
        """Score every child.

        Args:
            inputs: The scored fields.

        Returns:
            The penalty and the mark of each child.
        """
        return self.table.score(inputs)
