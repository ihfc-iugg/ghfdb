"""The borehole and mine rules.

They give the T-score of a gradient and the TC-score of a conductivity. The criteria are
declared here as tables (see ``penalties``). Only what a table cannot say is code: which
of the three cases a gradient is, and the interval depth gate.
"""

import numpy
import pandas

from ghfdb.fields import Field
from ghfdb.qc.engine.domain import DomainScores, DomainScoring
from ghfdb.qc.engine.rule_kinds import Condition
from ghfdb.qc.engine.tables import (
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
from ghfdb.qc.probe import (
    AMBIENT_OR_UNSPECIFIED,
    DRY_UNSPECIFIED_OR_OTHER,
    FULL_IN_SITU,
    PARTIAL_IN_SITU,
)
from ghfdb.vocabularies import concepts

CORR_IS_FLAG = concepts.corr_IS_flag
T_METHOD = concepts.T_method_top
TC_LOCATION = concepts.tc_location
TC_SATURATION = concepts.tc_saturation
TC_SOURCE = concepts.tc_source
TC_PT_CONDITIONS = concepts.tc_pT_conditions

# A gradient is a continuous log only with more than this many recordings.
CONTINUOUS_LOG_RECORDINGS = 3
# The TC-score of a conductivity that reports neither end of its interval.
GATE_SCORE = 0.1

ESTIMATED_TEMPERATURE = (
    T_METHOD.CPD,
    T_METHOD.XEN,
    T_METHOD.GTM,
    T_METHOD.BSR,
    T_METHOD.unspecified,
    T_METHOD.other,
)
TEMPERATURE_METHODS = (Field.T_method_top, Field.T_method_bottom)
INTERVAL_DEPTHS = (Field.q_top, Field.q_bottom)

CONTINUOUS_LOG = Criterion(
    "borehole-t.continuous-log",
    "Continuous log",
    Classes(
        TEMPERATURE_METHODS,
        (
            Group(0.1, (T_METHOD.LOGeq, T_METHOD.cLOG, T_METHOD.DTSeq, T_METHOD.cDTS)),
            Group(-0.1, (T_METHOD.LOGpert,)),
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
                    T_METHOD.LOGeq,
                    T_METHOD.cLOG,
                    T_METHOD.cBHT,
                    T_METHOD["HT-FT"],
                    T_METHOD["cHT-FT"],
                    T_METHOD.RTDeq,
                    T_METHOD.cRTD,
                    T_METHOD["ODTT-PC"],
                    T_METHOD["ODTT-TP"],
                    T_METHOD.EGRT,
                    T_METHOD.GRT,
                ),
            ),
            Group(
                -0.3,
                (
                    T_METHOD.LOGpert,
                    T_METHOD.DTSpert,
                    T_METHOD.BHT,
                    T_METHOD["HT-FTpert"],
                    T_METHOD.RTDpert,
                    T_METHOD.BLK,
                ),
            ),
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
                (
                    T_METHOD.cBHT,
                    T_METHOD.cDST,
                    T_METHOD.RTDeq,
                    T_METHOD.cRTD,
                    T_METHOD["ODTT-PC"],
                    T_METHOD["ODTT-TP"],
                    T_METHOD["cHT-FT"],
                    T_METHOD.EGRT,
                    T_METHOD.GRT,
                ),
            ),
            Group(-0.5, (T_METHOD.BHT, T_METHOD["HT-FTpert"], T_METHOD.RTDpert)),
            Group(-0.6, ESTIMATED_TEMPERATURE),
        ),
        skip_empty=True,
    ),
    "Table 3, Source type and number of T points",
)
TOP_METHOD_IS_SURFACE = Condition(Field.T_method_top, (T_METHOD.SUR,))

LOCATION = Criterion(
    "borehole-tc.location",
    "Conductivity location",
    Classes(
        (Field.tc_location,),
        (
            Group(0.0, (TC_LOCATION.actual,)),
            Group(-0.1, (TC_LOCATION.other,)),
            Group(-0.2, (TC_LOCATION.literature,)),
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
            Group(0.1, (TC_SOURCE["insitu-probe"], TC_SOURCE["core-log"])),
            Group(0.0, (TC_SOURCE["core-samples"],)),
            Group(
                -0.1,
                (
                    TC_SOURCE["cutting-samples"],
                    TC_SOURCE["outcrop-samples"],
                    TC_SOURCE["well-log"],
                ),
            ),
            Group(
                -0.2,
                (
                    TC_SOURCE["mineral-computation"],
                    TC_SOURCE.unspecified,
                    TC_SOURCE.other,
                    TC_SOURCE["assumed-from-literature"],
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
        left_out_when={Field.tc_location: (TC_LOCATION.literature,)},
    ),
    "Table 3, Number of conductivities",
)
SATURATION = Criterion(
    "borehole-tc.saturation",
    "Saturation",
    Classes(
        (Field.tc_saturation,),
        (
            Group(
                0.0, (TC_SATURATION.saturatedInSitu, TC_SATURATION.saturatedMeasured)
            ),
            Group(-0.1, (TC_SATURATION.saturatedCalculated, TC_SATURATION.recovered)),
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
            Group(0.0, (TC_PT_CONDITIONS.actualInSitu, *FULL_IN_SITU)),
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
                    Field.tc_pT_conditions: (
                        TC_PT_CONDITIONS.actualInSitu,
                        *FULL_IN_SITU,
                    ),
                    Field.corr_IS_flag: (CORR_IS_FLAG.consideredPT,),
                },
            ),
            Case(
                -0.1,
                {
                    Field.tc_pT_conditions: PARTIAL_IN_SITU,
                    Field.corr_IS_flag: (
                        CORR_IS_FLAG.consideredP,
                        CORR_IS_FLAG.consideredT,
                    ),
                },
            ),
            Case(
                -0.2,
                {
                    Field.tc_pT_conditions: AMBIENT_OR_UNSPECIFIED,
                    Field.corr_IS_flag: (
                        CORR_IS_FLAG.notConsidered,
                        CORR_IS_FLAG.unspecified,
                    ),
                },
            ),
        )
    ),
    "Table 3, pT conditions",
)

T_CRITERIA = (CONTINUOUS_LOG, SINGLE_POINTS, SURFACE_PLUS_ONE_POINT)
TC_CRITERIA = (LOCATION, SOURCE, NUMBER, SATURATION, CONDITIONS_AGREEING)


class BoreholeAndMine(DomainScoring):
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
        field, surface = TOP_METHOD_IS_SURFACE.field, TOP_METHOD_IS_SURFACE.concepts
        top = self.inputs.concepts(field)
        return self.inputs.any_value(top.isin(self.inputs.expand(field, surface)))

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
            filled & ~CONTINUOUS_LOG.table.fits(methods, self.inputs),
            index=methods.index,
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

    def scores(self) -> DomainScores:
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
        return DomainScores(t=t, tc=self.gated(tc), own_t=t, own_tc=self.gated(own_tc))
