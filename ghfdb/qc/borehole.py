"""The borehole and mine rules: the T-score of a gradient and the TC-score of a probe.

The criteria are declared here as tables (see ``penalties``). Only what a table cannot
say is code: which of the three cases a gradient is, the interval depth gate, and the
agreement of the pT conditions with the in-situ correction.
"""

from dataclasses import dataclass

import numpy
import pandas

from ghfdb.fields import Field
from ghfdb.qc.concepts import (
    ACTUAL_IN_SITU,
    ACTUAL_LOCATION,
    AMBIENT_OR_UNSPECIFIED,
    ASSUMED_FROM_LITERATURE,
    BHT,
    BLK,
    BSR,
    C_BHT,
    C_DTS,
    C_HT_FT,
    C_LOG,
    C_RTD,
    CONSIDERED_P,
    CONSIDERED_PT,
    CONSIDERED_T,
    CORE_LOG,
    CORE_SAMPLES,
    CPD,
    CUTTING_SAMPLES,
    DRY_UNSPECIFIED_OR_OTHER,
    DTS_EQ,
    DTS_PERT,
    EGRT,
    FULL_IN_SITU,
    GRT,
    GTM,
    HT_FT,
    HT_FT_PERT,
    IN_SITU_PROBE,
    LITERATURE_OR_UNSPECIFIED,
    LOG_EQ,
    LOG_PERT,
    MINERAL_COMPUTATION,
    NOT_CONSIDERED,
    ODTT_PC,
    ODTT_TP,
    OTHER_LOCATION,
    OTHER_SOURCE,
    OTHER_TEMPERATURE,
    OUTCROP_SAMPLES,
    PARTIAL_IN_SITU,
    RECOVERED,
    RTD_EQ,
    RTD_PERT,
    SATURATED_CALCULATED,
    SATURATED_IN_SITU,
    SATURATED_MEASURED,
    SURFACE,
    UNSPECIFIED_CORRECTION,
    UNSPECIFIED_SOURCE,
    UNSPECIFIED_TEMPERATURE,
    WELL_LOG,
    XEN,
)
from ghfdb.qc.inputs import Inputs
from ghfdb.qc.penalties import (
    Band,
    Bands,
    Case,
    Cases,
    Classes,
    Criterion,
    Group,
    Outcome,
    Penalty,
    Score,
    Table,
)
from ghfdb.qc.rules import Condition

# A gradient is a continuous log only with more than this many recordings.
CONTINUOUS_LOG_RECORDINGS = 3
# The TC-score of a conductivity that reports neither end of its interval.
GATE_SCORE = 0.1

ESTIMATED_TEMPERATURE = (
    CPD,
    XEN,
    GTM,
    BSR,
    UNSPECIFIED_TEMPERATURE,
    OTHER_TEMPERATURE,
)
TEMPERATURE_METHODS = (Field.T_method_top, Field.T_method_bottom)
LARGEST_CONTINUOUS_LOG = Outcome(-0.1, marked=True)
LARGEST_SINGLE_POINTS = Outcome(-0.5, marked=True)
LARGEST_SURFACE_PLUS_ONE_POINT = Outcome(-0.6, marked=True)

CONTINUOUS_LOG = Criterion(
    "borehole-t.continuous-log",
    "Continuous log",
    Classes(
        TEMPERATURE_METHODS,
        (
            Group(0.1, (LOG_EQ, C_LOG, DTS_EQ, C_DTS)),
            Group(-0.1, (LOG_PERT,)),
        ),
        empty=LARGEST_CONTINUOUS_LOG,
        unmatched=LARGEST_CONTINUOUS_LOG,
        skip_empty=True,
    ),
    "Table 3, Source type and number of T points",
)
SINGLE_POINTS = Criterion(
    "borehole-t.single-points",
    "Multiple single points",
    Classes(
        TEMPERATURE_METHODS,
        (
            Group(
                -0.1,
                (
                    LOG_EQ,
                    C_LOG,
                    C_BHT,
                    HT_FT,
                    C_HT_FT,
                    RTD_EQ,
                    C_RTD,
                    ODTT_PC,
                    ODTT_TP,
                    EGRT,
                    GRT,
                    C_DTS,
                ),
            ),
            Group(-0.3, (LOG_PERT, DTS_PERT, BHT, HT_FT_PERT, RTD_PERT, BLK)),
            Group(-0.5, ESTIMATED_TEMPERATURE),
        ),
        empty=LARGEST_SINGLE_POINTS,
        unmatched=LARGEST_SINGLE_POINTS,
        skip_empty=True,
    ),
    "Table 3, Source type and number of T points",
)
SURFACE_PLUS_ONE_POINT = Criterion(
    "borehole-t.surface-plus-one-point",
    "Surface temperature plus one point",
    Classes(
        (Field.T_method_bottom,),
        (
            Group(
                -0.3,
                (C_BHT, RTD_EQ, C_RTD, ODTT_PC, ODTT_TP, C_HT_FT, EGRT, GRT),
            ),
            Group(-0.5, (BHT, HT_FT_PERT, RTD_PERT)),
            Group(-0.6, ESTIMATED_TEMPERATURE),
        ),
        empty=LARGEST_SURFACE_PLUS_ONE_POINT,
        unmatched=LARGEST_SURFACE_PLUS_ONE_POINT,
        skip_empty=True,
    ),
    "Table 3, Source type and number of T points",
)
TOP_METHOD_IS_SURFACE = Condition(Field.T_method_top, (SURFACE,))

LOCATION = Criterion(
    "borehole-tc.location",
    "Conductivity location",
    Classes(
        (Field.tc_location,),
        (
            Group(0.0, (ACTUAL_LOCATION,)),
            Group(-0.1, (OTHER_LOCATION,)),
            Group(-0.2, (LITERATURE_OR_UNSPECIFIED,)),
        ),
    ),
    "Table 3, Localization",
)
SOURCE = Criterion(
    "borehole-tc.source",
    "Conductivity source",
    Classes(
        (Field.tc_source,),
        (
            Group(0.1, (IN_SITU_PROBE, CORE_LOG)),
            Group(0.0, (CORE_SAMPLES,)),
            Group(-0.1, (CUTTING_SAMPLES, OUTCROP_SAMPLES, WELL_LOG)),
            Group(
                -0.2,
                (
                    MINERAL_COMPUTATION,
                    UNSPECIFIED_SOURCE,
                    OTHER_SOURCE,
                    ASSUMED_FROM_LITERATURE,
                ),
            ),
        ),
    ),
    "Table 3, Source type",
)
NUMBER = Criterion(
    "borehole-tc.number",
    "Number of conductivity measurements",
    Bands(
        Field.tc_number,
        (Band(0.0, 15), Band(-0.1)),
        empty=Outcome(-0.1, marked=True),
        left_out_when={Field.tc_location: (LITERATURE_OR_UNSPECIFIED,)},
    ),
    "Table 3, Number of conductivities",
)
SATURATION = Criterion(
    "borehole-tc.saturation",
    "Saturation",
    Classes(
        (Field.tc_saturation,),
        (
            Group(0.0, (SATURATED_IN_SITU, SATURATED_MEASURED)),
            Group(-0.1, (SATURATED_CALCULATED, RECOVERED)),
            Group(-0.2, DRY_UNSPECIFIED_OR_OTHER),
        ),
    ),
    "Table 3, Saturation",
)
CONDITIONS = Criterion(
    "borehole-tc.pT",
    "pT conditions",
    Classes(
        (Field.tc_pT_conditions,),
        (
            Group(0.0, (ACTUAL_IN_SITU, *FULL_IN_SITU)),
            Group(-0.1, PARTIAL_IN_SITU),
            Group(-0.2, AMBIENT_OR_UNSPECIFIED),
        ),
    ),
    "Table 3, pT conditions",
)
CONDITIONS_AGREEING = Criterion(
    "borehole-tc.pT-agreement",
    "pT conditions must agree with the in-situ correction",
    Cases(
        (
            Case(
                0.0,
                {
                    Field.tc_pT_conditions: (ACTUAL_IN_SITU, *FULL_IN_SITU),
                    Field.corr_IS_flag: (CONSIDERED_PT,),
                },
            ),
            Case(
                -0.1,
                {
                    Field.tc_pT_conditions: PARTIAL_IN_SITU,
                    Field.corr_IS_flag: (CONSIDERED_P, CONSIDERED_T),
                },
            ),
            Case(
                -0.2,
                {
                    Field.tc_pT_conditions: AMBIENT_OR_UNSPECIFIED,
                    Field.corr_IS_flag: (NOT_CONSIDERED, UNSPECIFIED_CORRECTION),
                },
            ),
        )
    ),
    "Table 3, pT conditions",
)

T_CRITERIA = (CONTINUOUS_LOG, SINGLE_POINTS, SURFACE_PLUS_ONE_POINT)
CONDUCTIVITY_CRITERIA = (LOCATION, SOURCE, NUMBER, SATURATION)
TC_CRITERIA = (*CONDUCTIVITY_CRITERIA, CONDITIONS, CONDITIONS_AGREEING)


@dataclass(frozen=True)
class BoreholeRules:
    """Score the children explored by drilling, mining or indirect methods.

    A field that holds several values is scored value by value and the poorest counts
    (docs/reference/quality-scheme/index.md, "Several values in one field").

    Attributes:
        inputs: The scored fields of the children.
        routed: Whether the borehole and mine rules score each child, in the order of
            the children.
    """

    inputs: Inputs
    routed: numpy.ndarray

    @staticmethod
    def concepts() -> tuple[tuple[str, str], ...]:
        """List the concepts the rules name, with their fields.

        Returns:
            The concepts of the criteria and of the top method that makes a gradient a
            surface plus one point.
        """
        criteria = (*T_CRITERIA, *TC_CRITERIA)
        surface = TOP_METHOD_IS_SURFACE
        return (
            *(pair for criterion in criteria for pair in criterion.concepts()),
            *((surface.field, uri) for uri in surface.concepts),
        )

    def surface_case(self) -> numpy.ndarray:
        """Find the gradients that are a surface plus one point.

        See docs/reference/quality-scheme/borehole-and-mine.md, "Which case applies".

        Returns:
            Whether any top method of each child is the surface temperature.
        """
        top = self.inputs.concepts(TOP_METHOD_IS_SURFACE.field)
        return self.inputs.any_value(top.isin(TOP_METHOD_IS_SURFACE.concepts))

    def continuous_log_case(self, surface: numpy.ndarray) -> numpy.ndarray:
        """Find the gradients that are a continuous log.

        See docs/reference/quality-scheme/borehole-and-mine.md, "Which case applies".

        Args:
            surface: Whether each child is a surface plus one point, which is never a
                continuous log.

        Returns:
            Whether each child has more than three recordings, at least one method, and
            no method outside the continuous log's.
        """
        methods = pandas.concat(
            [self.inputs.concepts(field) for field in TEMPERATURE_METHODS]
        )
        filled = methods.notna().to_numpy()
        outside = pandas.Series(
            filled & ~CONTINUOUS_LOG.table.fits(methods), index=methods.index
        )
        recordings = self.inputs.every_value(
            self.inputs.numbers(Field.T_number) > CONTINUOUS_LOG_RECORDINGS
        )
        has_methods = self.inputs.any_value(pandas.Series(filled, index=methods.index))
        return numpy.asarray(
            ~surface & recordings & has_methods & ~self.inputs.any_value(outside),
            dtype=bool,
        )

    def temperature_methods(self) -> Penalty:
        """Score the temperature methods at the top and the bottom of the interval.

        The gradient is scored in the one case it is: a surface plus one point, a
        continuous log, or else multiple single points. See
        docs/reference/quality-scheme/borehole-and-mine.md, "T-score".

        Returns:
            The penalty and the mark of each child.
        """
        surface = self.surface_case()
        continuous = self.continuous_log_case(surface)
        log, points, surface_points = (
            criterion.score(self.inputs) for criterion in T_CRITERIA
        )
        conditions = [surface, continuous]
        return Penalty(
            pandas.Series(
                numpy.select(
                    conditions,
                    [surface_points.value.to_numpy(), log.value.to_numpy()],
                    points.value.to_numpy(),
                ),
                index=self.inputs.index,
            ),
            pandas.Series(
                numpy.select(
                    conditions,
                    [surface_points.marked.to_numpy(), log.marked.to_numpy()],
                    points.marked.to_numpy(),
                ),
                index=self.inputs.index,
            ),
        )

    def t_score(self) -> Score:
        """Score the gradient of each child.

        It reads nothing from the child, so the child's own score is the same (see
        ``own_t_score``).

        Returns:
            The T-score and its mark for each child.
        """
        return Score.total([self.temperature_methods()], self.routed)

    def own_t_score(self) -> Score:
        """Score the gradient on its own, which is its score for the child.

        Returns:
            The own T-score and its mark for each child.
        """
        return self.t_score()

    def depth_reported(self) -> numpy.ndarray:
        """Find the children that report the top or the bottom of the interval.

        Returns:
            Whether the top or the bottom of the interval is filled for each child.
        """
        top, bottom = (
            self.inputs.first(self.inputs.numbers(field)).notna().to_numpy()
            for field in (Field.q_top, Field.q_bottom)
        )
        return top | bottom

    def conductivity(self, conditions: Criterion[Table]) -> Score:
        """Add the criteria of the TC-score, behind the interval depth gate.

        See docs/reference/quality-scheme/borehole-and-mine.md, "Interval depth gate".

        Args:
            conditions: The criterion that scores the pressure and temperature
                conditions.

        Returns:
            The score and its mark for each child: ``0.1`` with the mark where neither
            depth is reported, and nothing else scored.
        """
        penalties = [
            criterion.score(self.inputs)
            for criterion in (*CONDUCTIVITY_CRITERIA, conditions)
        ]
        scored = Score.total(penalties, self.routed)
        closed = self.routed & ~self.depth_reported()
        return Score(
            scored.value.mask(closed, GATE_SCORE), scored.marked.mask(closed, True)
        )

    def tc_score(self) -> Score:
        """Score the conductivity of each child, with its in-situ correction.

        The pT conditions must agree with the child's in-situ correction.

        Returns:
            The TC-score and its mark for each child.
        """
        return self.conductivity(CONDITIONS_AGREEING)

    def own_tc_score(self) -> Score:
        """Score the conductivity on its own, before the child's correction applies.

        See docs/reference/quality-scheme/index.md, "Scores of a child and of its
        measurements".

        Returns:
            The own TC-score and its mark for each child.
        """
        return self.conductivity(CONDITIONS)
