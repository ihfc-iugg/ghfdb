"""The borehole and mine rules.

They give the T-score of a gradient and the TC-score of a conductivity. The criteria are
declared here as tables (see ``penalties``). Only what a table cannot say is code: which
of the three cases a gradient is, and the interval depth gate.
"""

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
    C_DST,
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
from ghfdb.qc.penalties import (
    Band,
    Bands,
    Case,
    Cases,
    Classes,
    Criterion,
    Group,
    Penalty,
    Score,
)
from ghfdb.qc.rules import Condition
from ghfdb.qc.ruleset import RuleScores, RuleSet

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
INTERVAL_DEPTHS = (Field.q_top, Field.q_bottom)

CONTINUOUS_LOG = Criterion(
    "borehole-t.continuous-log",
    "Continuous log",
    Classes(
        TEMPERATURE_METHODS,
        (
            Group(0.1, (LOG_EQ, C_LOG, DTS_EQ, C_DTS)),
            Group(-0.1, (LOG_PERT,)),
        ),
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
                ),
            ),
            Group(-0.3, (LOG_PERT, DTS_PERT, BHT, HT_FT_PERT, RTD_PERT, BLK)),
            Group(-0.5, ESTIMATED_TEMPERATURE),
        ),
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
                (C_BHT, C_DST, RTD_EQ, C_RTD, ODTT_PC, ODTT_TP, C_HT_FT, EGRT, GRT),
            ),
            Group(-0.5, (BHT, HT_FT_PERT, RTD_PERT)),
            Group(-0.6, ESTIMATED_TEMPERATURE),
        ),
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
TC_CRITERIA = (LOCATION, SOURCE, NUMBER, SATURATION, CONDITIONS_AGREEING)


class BoreholeRules(RuleSet):
    """Score the children explored by drilling, mining or indirect methods.

    A field that holds several values is scored value by value and the poorest counts
    (docs/reference/quality-scheme/index.md, "Several values in one field"). The three
    criteria of the T-score are the three cases of a gradient, and the method
    ``temperature_methods`` chooses between them. The TC-score is the sum of
    ``TC_CRITERIA``, and a measurement on its own scores the pT conditions alone.
    """

    criteria = (*T_CRITERIA, *TC_CRITERIA)
    stand_ins = {CONDITIONS_AGREEING.identifier: CONDITIONS}
    conditions = (TOP_METHOD_IS_SURFACE,)
    extra_fields = (Field.T_number, *INTERVAL_DEPTHS)

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
        return Penalty.choose([surface, continuous], [surface_points, log], points)

    def depth_reported(self) -> numpy.ndarray:
        """Find the children that report the top or the bottom of the interval.

        Returns:
            Whether the top or the bottom of the interval is filled for each child.
        """
        top, bottom = (
            self.inputs.first(self.inputs.numbers(field)).notna().to_numpy()
            for field in INTERVAL_DEPTHS
        )
        return top | bottom

    def gated(self, penalties: list[Penalty]) -> Score:
        """Add the penalties of the TC-score, behind the interval depth gate.

        See docs/reference/quality-scheme/borehole-and-mine.md, "Interval depth gate".

        Args:
            penalties: The penalty of each criterion of the TC-score.

        Returns:
            The score and its mark for each child: ``0.1`` with the mark where neither
            depth is reported, and nothing else scored.
        """
        scored = Score.total(penalties, self.routed)
        closed = self.routed & ~self.depth_reported()
        return Score(
            scored.value.mask(closed, GATE_SCORE), scored.marked.mask(closed, True)
        )

    def scores(self) -> RuleScores:
        """Score every child, each criterion once.

        The gradient reads nothing from the child, so the own T-score is the T-score.
        The TC-score requires the pT conditions to agree with the child's in-situ
        correction, and the own TC-score scores the pT conditions alone. See
        docs/reference/quality-scheme/borehole-and-mine.md and
        docs/reference/quality-scheme/index.md, "Scores of a child and of its
        measurements".

        Returns:
            The four scores and their marks for each child.
        """
        t = Score.total([self.temperature_methods()], self.routed)
        tc, own_tc = self.penalties(TC_CRITERIA)
        return RuleScores(t=t, tc=self.gated(tc), own_t=t, own_tc=self.gated(own_tc))
