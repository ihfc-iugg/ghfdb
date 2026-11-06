"""The probe-sensing rules: the T-score of a gradient and the TC-score of a probe.

Every method works on the whole table of children at once. A criterion reads its fields
from ``Inputs`` and returns the penalty and the missing-information mark of every child.
"""

from collections.abc import Sequence
from dataclasses import dataclass

import numpy
import pandas

from ghfdb.qc.rules import EXPLORATION_METHOD, PROBE_SENSING
from ghfdb.qc.scheme import PRESENT_CORRECTED, TILT_CORRECTED, Inputs

LARGEST_PENALTY = -0.2
DECIMALS = 3


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
            child the probe-sensing rules do not score.
        marked: Whether the score carries the missing-information mark, ``<NA>`` where
            the score is.
    """

    value: pandas.Series
    marked: pandas.Series


class ProbeRules:
    """Score the children explored by probing: the T-score and the TC-score.

    A field that holds several values is scored value by value and the poorest counts
    (docs/reference/quality-scheme/index.md, "Several values in one field"). A criterion
    that reads several fields scores every combination of their values.

    Args:
        inputs: The scored fields of the children.

    Attributes:
        inputs: The scored fields of the children.
    """

    def __init__(self, inputs: Inputs) -> None:
        self.inputs = inputs

    def routed(self) -> pandas.Series:
        """Find the children the probe-sensing rules score.

        Returns:
            Whether the first exploration method of each child is a probing method.
        """
        methods = self.inputs.first(self.inputs.concepts[EXPLORATION_METHOD])
        return methods.isin(PROBE_SENSING.concepts)

    def poorest(self, penalty: pandas.Series, marked: pandas.Series) -> Penalty:
        """Keep the poorest of the values of each child.

        Args:
            penalty: The penalty of every value, under the index of its child.
            marked: Whether each value sets the mark.

        Returns:
            The lowest penalty of each child, marked when a value with that penalty is.
        """
        lowest = penalty.groupby(level=0, sort=False).transform("min")
        chosen = marked & (penalty == lowest)
        return Penalty(
            penalty.groupby(level=0, sort=False).min().reindex(self.inputs.index),
            chosen.groupby(level=0, sort=False).any().reindex(self.inputs.index),
        )

    def combinations(self, fields: dict[str, pandas.Series]) -> pandas.DataFrame:
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
        self, rows: pandas.DataFrame, cases: Sequence[tuple[float, pandas.Series]]
    ) -> Penalty:
        """Score a list of cases: the poorest case that holds counts.

        Args:
            rows: The combinations of values.
            cases: The penalty of each case and whether it holds in each row.

        Returns:
            The poorest penalty of each child: ``-0.2`` with the mark when a field
            of the rows is empty, and ``-0.2`` without it when no case holds.
        """
        penalties = numpy.column_stack(
            [
                numpy.where(holds.to_numpy(dtype=bool), penalty, numpy.inf)
                for penalty, holds in cases
            ]
        ).min(axis=1)
        empty = rows.isna().any(axis=1)
        penalty = pandas.Series(
            numpy.where(numpy.isinf(penalties) | empty, LARGEST_PENALTY, penalties),
            index=rows.index,
        )
        return self.poorest(penalty, empty)

    def bands(
        self,
        numbers: pandas.Series,
        edges: Sequence[tuple[float, float]],
        penalty_below: float = LARGEST_PENALTY,
    ) -> Penalty:
        """Score numbers in bands that are open at the lower end.

        Args:
            numbers: The parsed values of a field.
            edges: A lower edge and the penalty of a number above it, largest first.
            penalty_below: The penalty of a number at or below every edge.

        Returns:
            The poorest penalty of each child, with the mark where the number is empty.
        """
        conditions = [numbers > edge for edge, _ in edges]
        choices = [penalty for _, penalty in edges]
        penalty = pandas.Series(
            numpy.select(conditions, choices, penalty_below), index=numbers.index
        )
        return self.poorest(penalty, numbers.isna())

    def waive(self, penalty: Penalty, code: str, concept: str) -> Penalty:
        """Take away a penalty and its mark from the children a correction waives.

        Args:
            penalty: The criterion's penalty.
            code: The code of the correction field, read at its first value.
            concept: The concept of the correction that waives the criterion.

        Returns:
            The penalty, ``0`` without the mark where the correction is the concept.
        """
        waived = self.inputs.first(self.inputs.concepts[code]).eq(concept).fillna(False)
        return Penalty(
            penalty.value.mask(waived, 0.0), penalty.marked.mask(waived, False)
        )

    def penetration(self) -> Penalty:
        """Score the probe penetration, ``C6``, in metres.

        See docs/reference/quality-scheme/probe-sensing.md, "Penetration".

        Returns:
            The penalty and the mark of each child.
        """
        return self.bands(self.inputs.numbers["C6"], [(10, 0.1), (3, 0.0), (1, -0.1)])

    def recordings(self) -> Penalty:
        """Score the number of temperature recordings, ``C37``.

        See docs/reference/quality-scheme/probe-sensing.md, "Number of temperature
        recordings".

        Returns:
            The penalty and the mark of each child.
        """
        numbers = self.inputs.numbers["C37"]
        return self.bands(numbers, [(5, 0.1), (2, 0.0), (1, -0.1)])

    def water_depth(self) -> Penalty:
        """Score the water depth, the elevation ``P6`` with its sign reversed.

        An elevation of zero or above has no water depth and counts as empty. This is
        the criterion before the bottom-water correction waives it. See
        docs/reference/quality-scheme/probe-sensing.md, "Water depth".

        Returns:
            The penalty and the mark of each child.
        """
        elevation = self.inputs.numbers["P6"]
        depth = (-elevation).where(elevation < 0)
        return self.bands(depth, [(2500, 0.0), (1500, -0.1)])

    def tilt(self) -> Penalty:
        """Score the probe tilt, ``C23``, in degrees.

        A tilt below zero fits no class and takes the largest penalty without the mark.
        This is the criterion before the tilt correction waives it. See
        docs/reference/quality-scheme/probe-sensing.md, "Tilt".

        Returns:
            The penalty and the mark of each child.
        """
        degrees = self.inputs.numbers["C23"]
        penalty = pandas.Series(
            numpy.select(
                [degrees > 30, degrees > 10, degrees >= 0],
                [LARGEST_PENALTY, -0.1, 0.0],
                LARGEST_PENALTY,
            ),
            index=degrees.index,
        )
        return self.poorest(penalty, degrees.isna())

    def total(self, criteria: Sequence[Penalty]) -> Score:
        """Add the penalties of the criteria to 1.0 for the children these rules score.

        Args:
            criteria: The penalty of each criterion.

        Returns:
            The score rounded to three places and whether any criterion sets the mark,
            ``<NA>`` for a child these rules do not score.
        """
        value = sum(
            (criterion.value for criterion in criteria),
            pandas.Series(1.0, index=self.inputs.index),
        )
        marked = pandas.concat(
            [criterion.marked for criterion in criteria], axis=1
        ).any(axis=1)
        routed = self.routed()
        return Score(
            value.round(DECIMALS).astype("Float64").where(routed),
            marked.astype("boolean").where(routed),
        )

    def t_score(self) -> Score:
        """Score the gradient of each child, with both corrections applied.

        A tilt correction waives the tilt criterion and a bottom-water correction waives
        the water-depth criterion (docs/reference/quality-scheme/probe-sensing.md,
        "T-score").

        Returns:
            The T-score and its mark for each child.
        """
        return self.total(
            [
                self.penetration(),
                self.recordings(),
                self.waive(self.water_depth(), "C17", PRESENT_CORRECTED),
                self.waive(self.tilt(), "C12", TILT_CORRECTED),
            ]
        )

    def own_t_score(self) -> Score:
        """Score the gradient on its own, before the child's corrections apply.

        See docs/reference/quality-scheme/index.md, "Scores of a child and of its
        measurements".

        Returns:
            The own T-score and its mark for each child.
        """
        return self.total(
            [self.penetration(), self.recordings(), self.water_depth(), self.tilt()]
        )
