"""Penalties, and the three kinds of table that give them.

A criterion of the quality scheme is a table that gives each value of a field, or each
combination of values of several fields, a penalty. There are three kinds:

* ``Bands``: a number against ordered edges.
* ``Classes``: a term against groups of concepts.
* ``Cases``: rows of conditions on several fields, the poorest row that holds counting.

Each table scores every child at once from ``Inputs`` and keeps the poorest of a
child's values. A value that has no penalty of its own, because it is empty or fits no
row, takes the largest penalty of the table. The table declares only whether that sets
the missing-information mark.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol, Self

import numpy
import pandas
from rdflib import URIRef

from ghfdb.fields import Field
from ghfdb.qc.inputs import Inputs

SCORE_DECIMALS = 3
Conditions = Mapping[Field, Sequence[URIRef]]


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
    def settle(
        cls,
        table: "Table",
        index: pandas.Index,
        penalty: numpy.ndarray,
        matched: numpy.ndarray,
        empty: numpy.ndarray,
    ) -> Self:
        """Give every value its penalty, or the largest penalty of its table.

        Args:
            table: The table that scores the values.
            index: The index of the values.
            penalty: The penalty of each value that matched.
            matched: Whether each value matched a row of the table.
            empty: Whether each value is empty, whatever the rows hold.

        Returns:
            The penalty of each value, and whether it sets the mark.
        """
        marked = numpy.where(
            empty, table.empty_marked, ~matched & table.unmatched_marked
        )
        return cls(
            pandas.Series(numpy.where(matched, penalty, table.largest()), index=index),
            pandas.Series(marked, index=index),
        )

    @classmethod
    def choose(
        cls,
        conditions: Sequence[numpy.ndarray],
        choices: Sequence[Self],
        default: Self,
    ) -> Self:
        """Take the penalty of the first choice whose condition holds, for each child.

        Args:
            conditions: Whether each choice applies to each child.
            choices: The penalty to take for each condition, in the same order.
            default: The penalty of a child no condition holds for.

        Returns:
            The chosen penalty and mark of each child.
        """
        return cls(
            pandas.Series(
                numpy.select(
                    conditions,
                    [choice.value.to_numpy() for choice in choices],
                    default.value.to_numpy(),
                ),
                index=default.value.index,
            ),
            pandas.Series(
                numpy.select(
                    conditions,
                    [choice.marked.to_numpy() for choice in choices],
                    default.marked.to_numpy(),
                ),
                index=default.marked.index,
            ),
        )

    def poorest(self, index: pandas.Index) -> Self:
        """Keep the poorest of the values of each child.

        Args:
            index: The index of the children. The penalty has a row for each value,
                under the index of its child.

        Returns:
            The lowest penalty of each child, marked when a value with that penalty is.
        """
        if self.value.index.is_unique:
            return type(self)(self.value.reindex(index), self.marked.reindex(index))
        lowest = self.value.groupby(level=0, sort=False).transform("min")
        chosen = self.marked & (self.value == lowest)
        return type(self)(
            self.value.groupby(level=0, sort=False).min().reindex(index),
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


class Table(Protocol):
    """What every kind of table offers."""

    @property
    def empty_marked(self) -> bool:
        """Whether an empty value sets the missing-information mark."""
        ...

    @property
    def unmatched_marked(self) -> bool:
        """Whether a value that fits no row sets the mark."""
        ...

    def reads(self) -> tuple[str, ...]:
        """List the fields the table reads."""
        ...

    def concepts(self) -> tuple[tuple[str, URIRef], ...]:
        """List the field and the URI of every concept the table names."""
        ...

    def largest(self) -> float:
        """Give the largest penalty of the table, its lowest."""
        ...

    def score(self, inputs: Inputs) -> Penalty:
        """Give the penalty of every child."""
        ...


@dataclass(frozen=True)
class Bands:
    """A number field against ordered edges.

    The first band that holds a number gives its penalty. A number that is empty or not
    a number, or that no band holds, takes the largest penalty of the table.

    Attributes:
        field: The number field.
        bands: The bands, the highest first.
        empty_marked: Whether an empty number sets the mark.
        unmatched_marked: Whether a number no band holds sets the mark.
        left_out_when: Conditions on other fields that leave the criterion out for a
            value: it then adds no penalty and no mark.
    """

    field: Field
    bands: tuple[Band, ...]
    empty_marked: bool = True
    unmatched_marked: bool = False
    left_out_when: Conditions | None = None

    def reads(self) -> tuple[str, ...]:
        """List the number field, then the fields of ``left_out_when``."""
        return (self.field, *(self.left_out_when or ()))

    def concepts(self) -> tuple[tuple[str, URIRef], ...]:
        """List the concepts of ``left_out_when``."""
        return tuple(
            (field, concept)
            for field, concepts in (self.left_out_when or {}).items()
            for concept in concepts
        )

    def largest(self) -> float:
        """Give the lowest penalty of the bands."""
        return min(band.value for band in self.bands)

    def read(self, inputs: Inputs) -> pandas.Series:
        """Read the numbers the bands hold.

        Args:
            inputs: The scored fields.

        Returns:
            The number of every value of the field, under its child's index.
        """
        return inputs.numbers(self.field)

    def values(self, numbers: pandas.Series) -> Penalty:
        """Give each number its penalty.

        Args:
            numbers: The numbers, one row for each value.

        Returns:
            The penalty of each number and whether it sets the mark.
        """
        chosen = Band.select(self.bands, numbers, numpy.nan)
        return Penalty.settle(
            self,
            numbers.index,
            chosen,
            ~numpy.isnan(chosen),
            numbers.isna().to_numpy(),
        )

    def score(self, inputs: Inputs) -> Penalty:
        """Score the number of every child.

        Args:
            inputs: The scored fields.

        Returns:
            The poorest penalty of each child.
        """
        numbers = self.read(inputs)
        if self.left_out_when is None:
            return self.values(numbers).poorest(inputs.index)
        rows = Inputs.combine(
            {
                self.field: numbers,
                **{field: inputs.concepts(field) for field in self.left_out_when},
            }
        )
        left_out = Case.hold_all(rows, self.left_out_when, inputs)
        return self.values(rows[self.field]).waived(left_out).poorest(inputs.index)


class Depths(Bands):
    """Bands of a depth below sea level, read from the elevation of the site.

    The depth is the elevation with its sign reversed. An elevation of zero or above has
    no depth, which counts as empty.
    """

    def read(self, inputs: Inputs) -> pandas.Series:
        """Read the depth of every value of the elevation.

        Args:
            inputs: The scored fields.

        Returns:
            The depth in the unit of the elevation, empty where the elevation is not
            below zero.
        """
        elevation = inputs.numbers(self.field)
        return (-elevation).where(elevation < 0)


@dataclass(frozen=True)
class Group:
    """Concepts that share a penalty.

    Attributes:
        penalty: The penalty.
        concepts: The concepts, or collections of the field's scheme.
    """

    penalty: float
    concepts: tuple[URIRef, ...]


@dataclass(frozen=True)
class Classes:
    """A term field against groups of concepts.

    A value takes the penalty of the group its concept is in. A value that is empty, or
    whose concept is in no group, takes the largest penalty of the table.

    Attributes:
        fields: The fields read. Their values are scored together, and the poorest
            counts.
        groups: The groups.
        empty_marked: Whether an empty value sets the mark.
        unmatched_marked: Whether a concept in no group sets the mark.
        skip_empty: Whether an empty value is left out when the child holds another,
            as the temperature method at one end of an interval is when the other end
            has one.
    """

    fields: tuple[Field, ...]
    groups: tuple[Group, ...]
    empty_marked: bool = True
    unmatched_marked: bool = True
    skip_empty: bool = False

    def reads(self) -> tuple[str, ...]:
        """List the fields."""
        return self.fields

    def concepts(self) -> tuple[tuple[str, URIRef], ...]:
        """List every concept of every group, for each field."""
        return tuple(
            (field, concept)
            for field in self.fields
            for group in self.groups
            for concept in group.concepts
        )

    def largest(self) -> float:
        """Give the lowest penalty of the groups."""
        return min(group.penalty for group in self.groups)

    def membership(
        self, concepts: pandas.Series, inputs: Inputs
    ) -> list[numpy.ndarray]:
        """Say which concepts are in each group.

        Args:
            concepts: The concept of every value.
            inputs: The scored fields, which expand a collection a group names. The
                fields of a table share one vocabulary.

        Returns:
            For each group, whether each concept is in it.
        """
        return [
            concepts.isin(inputs.expand(self.fields[0], group.concepts)).to_numpy(
                dtype=bool
            )
            for group in self.groups
        ]

    def fits(self, concepts: pandas.Series, inputs: Inputs) -> numpy.ndarray:
        """Say which concepts are in a group.

        Args:
            concepts: The concept of every value.
            inputs: The scored fields.

        Returns:
            Whether each concept is in a group.
        """
        return numpy.any(self.membership(concepts, inputs), axis=0)

    def values(self, concepts: pandas.Series, inputs: Inputs) -> Penalty:
        """Give each concept the penalty of its group.

        Args:
            concepts: The concept of every value.
            inputs: The scored fields.

        Returns:
            The penalty of each value and whether it sets the mark.
        """
        member = self.membership(concepts, inputs)
        return Penalty.settle(
            self,
            concepts.index,
            numpy.select(member, [group.penalty for group in self.groups], 0.0),
            numpy.any(member, axis=0),
            concepts.isna().to_numpy(),
        )

    def score(self, inputs: Inputs) -> Penalty:
        """Score every value of the fields of every child.

        Args:
            inputs: The scored fields.

        Returns:
            The poorest penalty of each child.
        """
        concepts = pandas.concat([inputs.concepts(field) for field in self.fields])
        penalty = self.values(concepts, inputs)
        if self.skip_empty:
            filled = concepts.notna()
            some_filled = filled.groupby(level=0, sort=False).transform("any")
            keep = (filled | ~some_filled).to_numpy()
            penalty = Penalty(penalty.value[keep], penalty.marked[keep])
        return penalty.poorest(inputs.index)


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

    def concepts(self) -> tuple[tuple[Field, URIRef], ...]:
        """List the concepts the row names, with their fields."""
        return tuple(
            (field, concept)
            for conditions in (self.conditions, self.every or {})
            for field, concepts in conditions.items()
            for concept in concepts
        )

    @staticmethod
    def hold_all(
        rows: pandas.DataFrame, conditions: Conditions, inputs: Inputs
    ) -> numpy.ndarray:
        """Say which rows satisfy every condition.

        Args:
            rows: The concepts of each field, one row for each combination of values.
            conditions: The concepts each named field may hold.
            inputs: The scored fields, which expand a collection a condition names.

        Returns:
            Whether every condition holds in each row. A row holds every condition of an
            empty set.
        """
        holds = numpy.ones(len(rows), dtype=bool)
        for field, concepts in conditions.items():
            holds &= (
                rows[field].isin(inputs.expand(field, concepts)).to_numpy(dtype=bool)
            )
        return holds

    def holds(self, rows: pandas.DataFrame, inputs: Inputs) -> numpy.ndarray:
        """Say which combinations of values the row holds for.

        Args:
            rows: The concepts of each field, one row for each combination of values.
            inputs: The scored fields, from which every value of a child is read.

        Returns:
            Whether the row holds in each combination.
        """
        holds = self.hold_all(rows, self.conditions, inputs)
        for field, concepts in (self.every or {}).items():
            every = pandas.Series(
                inputs.every_value(
                    inputs.concepts(field).isin(inputs.expand(field, concepts))
                ),
                index=inputs.index,
            )
            holds &= every.reindex(rows.index).to_numpy(dtype=bool)
        return holds


@dataclass(frozen=True)
class Cases:
    """Rows of conditions on several fields.

    Every row whose conditions all hold counts, and the poorest penalty wins. A row
    holds whatever the fields it does not name contain. A combination that no row holds
    takes the largest penalty of the table, which sets the mark when a field some row
    names is empty and ``unmatched_marked`` is set otherwise.

    Attributes:
        cases: The rows.
        empty_marked: Whether a combination no row holds, with an empty field some row
            names, sets the mark.
        unmatched_marked: Whether a combination no row holds, with no such field empty,
            sets the mark.
    """

    cases: tuple[Case, ...]
    empty_marked: bool = True
    unmatched_marked: bool = False

    def reads(self) -> tuple[str, ...]:
        """List the fields the rows name, in order of first mention."""
        return tuple(
            dict.fromkeys(field for case in self.cases for field in case.fields())
        )

    def concepts(self) -> tuple[tuple[str, URIRef], ...]:
        """List the concepts of every row, with their fields, each once."""
        return tuple(
            dict.fromkeys(pair for case in self.cases for pair in case.concepts())
        )

    def largest(self) -> float:
        """Give the lowest penalty of the rows."""
        return min(case.penalty for case in self.cases)

    def score(self, inputs: Inputs) -> Penalty:
        """Score every combination of the values of the fields of every child.

        Args:
            inputs: The scored fields.

        Returns:
            The poorest penalty of each child.
        """
        rows = Inputs.combine({field: inputs.concepts(field) for field in self.reads()})
        penalties = numpy.column_stack(
            [
                numpy.where(case.holds(rows, inputs), case.penalty, numpy.inf)
                for case in self.cases
            ]
        ).min(axis=1)
        matched = numpy.isfinite(penalties)
        empty = rows.isna().any(axis=1).to_numpy() & ~matched
        return Penalty.settle(self, rows.index, penalties, matched, empty).poorest(
            inputs.index
        )


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

    def concepts(self) -> tuple[tuple[str, URIRef], ...]:
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
