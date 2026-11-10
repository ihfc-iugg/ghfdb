"""The borehole and mine rules: the T-score of a gradient and the TC-score of a probe.

Every method works on the whole table of children at once. A criterion reads its fields
from ``Inputs`` and returns the penalty and the missing-information mark of every child.
"""

from collections.abc import Sequence

import numpy
import pandas

from ghfdb.qc.concepts import (
    ACTUAL_IN_SITU,
    ACTUAL_LOCATION,
    CONSIDERED_PT,
    CORE_SAMPLES,
    LITERATURE_OR_UNSPECIFIED,
    OTHER_LOCATION,
    RECOVERED,
    SATURATED_CALCULATED,
    SATURATED_IN_SITU,
    SATURATED_MEASURED,
    SURFACE,
)
from ghfdb.qc.rules import BOREHOLE, EXPLORATION_METHOD
from ghfdb.qc.scheme import (
    AMBIENT_OR_UNSPECIFIED,
    BEST_SOURCES,
    CONSIDERED_P_OR_T,
    CONTINUOUS_LOG_BEST,
    CONTINUOUS_LOG_METHODS,
    CONTINUOUS_LOG_PERTURBED,
    DRY_UNSPECIFIED_OR_OTHER,
    ESTIMATED_SOURCES,
    ESTIMATED_TEMPERATURE,
    FULL_IN_SITU,
    LARGEST_PENALTY,
    NOT_CONSIDERED_OR_UNSPECIFIED,
    PARTIAL_IN_SITU,
    SAMPLED_SOURCES,
    SINGLE_POINTS_EQUILIBRIUM,
    SINGLE_POINTS_PERTURBED,
    SURFACE_BOTTOM_CORRECTED,
    SURFACE_BOTTOM_PERTURBED,
    Inputs,
    Penalty,
    Score,
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
LOCATIONS: Groups = [
    (0.0, [ACTUAL_LOCATION]),
    (-0.1, [OTHER_LOCATION]),
    (LARGEST_PENALTY, [LITERATURE_OR_UNSPECIFIED]),
]
SOURCES: Groups = [
    (0.1, BEST_SOURCES),
    (0.0, [CORE_SAMPLES]),
    (-0.1, SAMPLED_SOURCES),
    (LARGEST_PENALTY, ESTIMATED_SOURCES),
]
SATURATIONS: Groups = [
    (0.0, [SATURATED_IN_SITU, SATURATED_MEASURED]),
    (-0.1, [SATURATED_CALCULATED, RECOVERED]),
    (LARGEST_PENALTY, DRY_UNSPECIFIED_OR_OTHER),
]
CONDITIONS: Groups = [
    (0.0, [ACTUAL_IN_SITU, *FULL_IN_SITU]),
    (-0.1, PARTIAL_IN_SITU),
    (LARGEST_PENALTY, AMBIENT_OR_UNSPECIFIED),
]
MEASUREMENTS_ABOVE = 15
GATE_SCORE = 0.1


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
        chosen = Penalty.poorest(
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
        return Score.total([self.temperature_methods()], self.routed())

    def own_t_score(self) -> Score:
        """Score the gradient on its own, which is its score for the child.

        Returns:
            The own T-score and its mark for each child.
        """
        return self.t_score()

    def depth_reported(self) -> pandas.Series:
        """Find the children that report the top or the bottom of the interval.

        Returns:
            Whether ``C4`` or ``C5`` is filled for each child.
        """
        numbers = self.inputs.numbers
        return (
            self.inputs.first(numbers["C4"]).notna()
            | self.inputs.first(numbers["C5"]).notna()
        )

    def single(self, code: str, groups: Groups) -> Penalty:
        """Score a field by the group each of its values belongs to.

        Args:
            code: The code of the field.
            groups: The penalty of each group and the concepts in it.

        Returns:
            The poorest penalty of each child, ``-0.2`` with the mark for an empty
            value.
        """
        graded = self.grade(self.inputs.concepts[code], groups, LARGEST_PENALTY)
        return Penalty.poorest(graded.value, graded.marked, self.inputs.index)

    def location(self) -> Penalty:
        """Score where the conductivity was measured, ``C42``.

        See docs/reference/quality-scheme/borehole-and-mine.md, "Location".

        Returns:
            The penalty and the mark of each child.
        """
        return self.single("C42", LOCATIONS)

    def source(self) -> Penalty:
        """Score where the conductivity comes from, ``C41``.

        See docs/reference/quality-scheme/borehole-and-mine.md, "Source".

        Returns:
            The penalty and the mark of each child.
        """
        return self.single("C41", SOURCES)

    def number(self) -> Penalty:
        """Score the number of conductivity measurements, ``C47``.

        The criterion is left out for a literature location, whatever the number. See
        docs/reference/quality-scheme/borehole-and-mine.md, "Number of conductivity
        measurements".

        Returns:
            The penalty and the mark of each child.
        """
        rows = Inputs.combinations(
            {
                "number": self.inputs.numbers["C47"],
                "location": self.inputs.concepts["C42"],
            }
        )
        numbers = rows["number"]
        penalty = pandas.Series(
            numpy.where(numbers > MEASUREMENTS_ABOVE, 0.0, -0.1), index=rows.index
        )
        skipped = rows["location"].eq(LITERATURE_OR_UNSPECIFIED).fillna(False)
        return Penalty.poorest(
            penalty.mask(skipped, 0.0),
            numbers.isna().mask(skipped, False),
            self.inputs.index,
        )

    def saturation(self) -> Penalty:
        """Score the saturation, ``C44``.

        See docs/reference/quality-scheme/borehole-and-mine.md, "Saturation".

        Returns:
            The penalty and the mark of each child.
        """
        return self.single("C44", SATURATIONS)

    def conditions(self) -> Penalty:
        """Score the pressure and temperature conditions with the in-situ correction.

        The conditions ``C45`` must agree with the child's correction ``C11``. See
        docs/reference/quality-scheme/borehole-and-mine.md, "Pressure and temperature
        conditions".

        Returns:
            The penalty and the mark of each child.
        """
        concepts = self.inputs.concepts
        rows = Inputs.combinations(
            {"conditions": concepts["C45"], "correction": concepts["C11"]}
        )
        conditions, correction = rows["conditions"], rows["correction"]
        return Penalty.cases(
            rows,
            [
                (
                    0.0,
                    conditions.isin([ACTUAL_IN_SITU, *FULL_IN_SITU])
                    & correction.eq(CONSIDERED_PT),
                ),
                (
                    -0.1,
                    conditions.isin(PARTIAL_IN_SITU)
                    & correction.isin(CONSIDERED_P_OR_T),
                ),
                (
                    LARGEST_PENALTY,
                    conditions.isin(AMBIENT_OR_UNSPECIFIED)
                    & correction.isin(NOT_CONSIDERED_OR_UNSPECIFIED),
                ),
            ],
            self.inputs.index,
        )

    def own_conditions(self) -> Penalty:
        """Score the pressure and temperature conditions alone, ``C45``.

        See docs/reference/quality-scheme/departures.md, "DEP-15".

        Returns:
            The penalty and the mark of each child.
        """
        return self.single("C45", CONDITIONS)

    def score(self, conditions: Penalty) -> Score:
        """Add the criteria of the TC-score, behind the interval depth gate.

        Args:
            conditions: The penalty of the pressure and temperature conditions.

        Returns:
            The score and its mark for each child: ``0.1`` with the mark where
            neither depth is reported, and nothing else scored.
        """
        scored = Score.total(
            [
                self.location(),
                self.source(),
                self.number(),
                self.saturation(),
                conditions,
            ],
            self.routed(),
        )
        closed = self.routed() & ~self.depth_reported()
        return Score(
            scored.value.mask(closed, GATE_SCORE), scored.marked.mask(closed, True)
        )

    def tc_score(self) -> Score:
        """Score the conductivity of each child, with its in-situ correction.

        See docs/reference/quality-scheme/borehole-and-mine.md, "TC-score".

        Returns:
            The TC-score and its mark for each child.
        """
        return self.score(self.conditions())

    def own_tc_score(self) -> Score:
        """Score the conductivity on its own, before the child's correction applies.

        See docs/reference/quality-scheme/index.md, "Scores of a child and of its
        measurements".

        Returns:
            The own TC-score and its mark for each child.
        """
        return self.score(self.own_conditions())
