"""The borehole and mine rules: the T-score of a gradient and the TC-score of a probe.

Every method works on the whole table of children at once. A criterion reads its fields
from ``Inputs`` and returns the penalty and the missing-information mark of every child.
"""

from collections.abc import Sequence

import numpy
import pandas

from ghfdb.qc.rules import BOREHOLE, EXPLORATION_METHOD
from ghfdb.qc.scheme import (
    CONTINUOUS_LOG_BEST,
    CONTINUOUS_LOG_METHODS,
    CONTINUOUS_LOG_PERTURBED,
    ESTIMATED_TEMPERATURE,
    SINGLE_POINTS_EQUILIBRIUM,
    SINGLE_POINTS_PERTURBED,
    SURFACE,
    SURFACE_BOTTOM_CORRECTED,
    SURFACE_BOTTOM_PERTURBED,
    Inputs,
    Penalty,
    Score,
    poorest,
    total,
)

Groups = Sequence[tuple[float, Sequence[str]]]

CONTINUOUS_LOG: Groups = [(0.1, CONTINUOUS_LOG_BEST), (-0.1, CONTINUOUS_LOG_PERTURBED)]
SINGLE_POINTS: Groups = [
    (-0.1, SINGLE_POINTS_EQUILIBRIUM),
    (-0.3, SINGLE_POINTS_PERTURBED),
    (-0.5, ESTIMATED_TEMPERATURE),
]
SURFACE_PLUS_ONE_POINT: Groups = [
    (-0.3, SURFACE_BOTTOM_CORRECTED),
    (-0.5, SURFACE_BOTTOM_PERTURBED),
    (-0.6, ESTIMATED_TEMPERATURE),
]
LARGEST_CONTINUOUS_LOG = -0.1
LARGEST_SINGLE_POINTS = -0.5
LARGEST_SURFACE_PLUS_ONE_POINT = -0.6
CONTINUOUS_LOG_RECORDINGS = 3


class BoreholeRules:
    """Score the children explored by drilling, mining or indirect methods.

    A field that holds several values is scored value by value and the poorest counts
    (docs/reference/quality-scheme/index.md, "Several values in one field").

    Args:
        inputs: The scored fields of the children.

    Attributes:
        inputs: The scored fields of the children.
    """

    def __init__(self, inputs: Inputs) -> None:
        self.inputs = inputs

    def routed(self) -> pandas.Series:
        """Find the children the borehole and mine rules score.

        Returns:
            Whether the first exploration method of each child is a borehole or mine
            method.
        """
        methods = self.inputs.first(self.inputs.concepts[EXPLORATION_METHOD])
        return methods.isin(BOREHOLE.concepts)

    def grade(self, concepts: pandas.Series, groups: Groups, largest: float) -> Penalty:
        """Give each value the penalty of the group it belongs to.

        Args:
            concepts: The concept of every value, under the index of its child.
            groups: The penalty of each group and the concepts in it.
            largest: The penalty of a value that is in no group, or empty.

        Returns:
            The penalty of every value, marked where the value is in no group.
        """
        matched = [concepts.isin(members).to_numpy(dtype=bool) for _, members in groups]
        penalty = numpy.select(matched, [penalty for penalty, _ in groups], largest)
        return Penalty(
            pandas.Series(penalty, index=concepts.index),
            pandas.Series(~numpy.any(matched, axis=0), index=concepts.index),
        )

    def log_cases(self) -> tuple[pandas.Series, pandas.Series]:
        """Find the children whose gradient is a surface plus one point or a log.

        See docs/reference/quality-scheme/borehole-and-mine.md, "Which case applies".

        Returns:
            Whether each child is the surface case, and whether it is a continuous log.
        """
        concepts = self.inputs.concepts
        index = self.inputs.index
        methods = pandas.concat([concepts["C31"], concepts["C32"]])
        surface = (
            concepts["C31"]
            .eq(SURFACE)
            .fillna(False)
            .groupby(level=0, sort=False)
            .any()
            .reindex(index)
        )
        recordings = (
            (self.inputs.numbers["C37"] > CONTINUOUS_LOG_RECORDINGS)
            .groupby(level=0, sort=False)
            .all()
            .reindex(index)
        )
        filled = methods.notna().groupby(level=0, sort=False).any().reindex(index)
        outside = (
            (methods.notna() & ~methods.isin(CONTINUOUS_LOG_METHODS))
            .groupby(level=0, sort=False)
            .any()
            .reindex(index)
        )
        return surface, ~surface & recordings & filled & ~outside

    def decide(
        self,
        methods: pandas.Series,
        surface: pandas.Series,
        continuous: pandas.Series,
        bottom: bool,
    ) -> Penalty:
        """Score the methods at one end of the interval in the child's case.

        Args:
            methods: The concept of every method, under the index of its child.
            surface: Whether each child is the surface plus one point case.
            continuous: Whether each child is a continuous log.
            bottom: Whether the methods are those at the bottom of the interval.

        Returns:
            The penalty of every method, empty where the method is empty or, in the
            surface case, at the top.
        """
        in_surface = surface.reindex(methods.index).to_numpy(dtype=bool)
        in_log = continuous.reindex(methods.index).to_numpy(dtype=bool)
        graded = [
            self.grade(methods, CONTINUOUS_LOG, LARGEST_CONTINUOUS_LOG),
            self.grade(methods, SURFACE_PLUS_ONE_POINT, LARGEST_SURFACE_PLUS_ONE_POINT),
            self.grade(methods, SINGLE_POINTS, LARGEST_SINGLE_POINTS),
        ]
        conditions = [in_log, in_surface]
        penalty = numpy.select(
            conditions, [g.value for g in graded[:2]], graded[2].value
        )
        marked = numpy.select(
            conditions, [g.marked for g in graded[:2]], graded[2].marked
        )
        counted = methods.notna().to_numpy(dtype=bool) & (bottom | ~in_surface)
        return Penalty(
            pandas.Series(penalty, index=methods.index).where(counted),
            pandas.Series(marked & counted, index=methods.index),
        )

    def temperature_methods(self) -> Penalty:
        """Score the temperature methods at the top and the bottom, ``C31`` and ``C32``.

        See docs/reference/quality-scheme/borehole-and-mine.md, "T-score".

        Returns:
            The penalty and the mark of each child.
        """
        concepts = self.inputs.concepts
        surface, continuous = self.log_cases()
        ends = [
            self.decide(concepts["C31"], surface, continuous, bottom=False),
            self.decide(concepts["C32"], surface, continuous, bottom=True),
        ]
        chosen = poorest(
            pandas.concat([end.value for end in ends]),
            pandas.concat([end.marked for end in ends]),
            self.inputs.index,
        )
        none = chosen.value.isna()
        largest = numpy.where(
            surface, LARGEST_SURFACE_PLUS_ONE_POINT, LARGEST_SINGLE_POINTS
        )
        return Penalty(
            chosen.value.fillna(pandas.Series(largest, index=self.inputs.index)),
            chosen.marked | none,
        )

    def t_score(self) -> Score:
        """Score the gradient of each child.

        It reads nothing from the child, so the child's own score is the same (see
        ``own_t_score``). See docs/reference/quality-scheme/borehole-and-mine.md,
        "T-score".

        Returns:
            The T-score and its mark for each child.
        """
        return total([self.temperature_methods()], self.routed())

    def own_t_score(self) -> Score:
        """Score the gradient on its own, which is its score for the child.

        Returns:
            The own T-score and its mark for each child.
        """
        return self.t_score()
