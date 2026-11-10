"""The probe-sensing rules.

They give the T-score of a gradient and the TC-score of a conductivity. The criteria are
declared here as tables (see ``penalties``), and the two corrections that waive a
criterion are declared beside them in ``ProbeRules``.
"""

from ghfdb.fields import Field
from ghfdb.qc.concepts import (
    ACTUAL_IN_SITU,
    ACTUAL_LOCATION,
    AMBIENT_OR_UNSPECIFIED,
    CHLORINE_CONTENT,
    DRY_UNSPECIFIED_OR_OTHER,
    FULL_IN_SITU,
    IN_SITU_PROBE,
    LABORATORY_OTHER,
    LINE_SOURCE_FULL,
    LINE_SOURCE_HALF,
    LITERATURE_OR_UNSPECIFIED,
    LITHOLOGY,
    MINERAL_COMPOSITION,
    OTHER_LOCATION,
    PARTIAL_IN_SITU,
    PLANE_SOURCE_FULL,
    PLANE_SOURCE_HALF,
    POINT_SOURCE,
    PRESENT_CORRECTED,
    PROBE_PULSE,
    RECOVERED,
    SATURATED_CALCULATED,
    SATURATED_IN_SITU,
    SATURATED_MEASURED,
    TILT_CORRECTED,
    UNSPECIFIED_METHOD,
    WATER_CONTENT,
    WELL_LOG_DETERMINISTIC,
    WELL_LOG_EMPIRICAL,
)
from ghfdb.qc.penalties import (
    Band,
    Bands,
    Case,
    Cases,
    Classes,
    Criterion,
    Depths,
    Group,
    Score,
)
from ghfdb.qc.rules import Condition
from ghfdb.qc.ruleset import RuleScores, RuleSet

LABORATORY_METHODS = (
    POINT_SOURCE,
    LINE_SOURCE_FULL,
    LINE_SOURCE_HALF,
    PLANE_SOURCE_FULL,
    PLANE_SOURCE_HALF,
    LABORATORY_OTHER,
)
ESTIMATED_FROM_LITERATURE = (LITHOLOGY, WELL_LOG_DETERMINISTIC, WELL_LOG_EMPIRICAL)
ESTIMATED_FROM_OTHER = (
    WATER_CONTENT,
    MINERAL_COMPOSITION,
    CHLORINE_CONTENT,
    UNSPECIFIED_METHOD,
)

PENETRATION = Criterion(
    "probe-t.penetration",
    "Probe penetration",
    Bands(
        Field.probe_penetration,
        (Band(0.1, 10), Band(0.0, 3), Band(-0.1, 1), Band(-0.2)),
    ),
    "Table 2, Probe penetration",
)
RECORDINGS = Criterion(
    "probe-t.recordings",
    "Number of temperature recordings",
    Bands(
        Field.T_number,
        (Band(0.1, 5), Band(0.0, 2), Band(-0.1, 1), Band(-0.2)),
    ),
    "Table 2, Number of temperature points",
)
WATER_DEPTH = Criterion(
    "probe-t.water-depth",
    "Water depth",
    Depths(Field.elevation, (Band(0.0, 2500), Band(-0.1, 1500), Band(-0.2))),
    "Table 2, Water depth",
)
TILT = Criterion(
    "probe-t.tilt",
    "Probe tilt",
    Bands(
        Field.probe_tilt,
        (Band(-0.2, 30), Band(-0.1, 10), Band(0.0, 0, inclusive=True)),
    ),
    "Table 2, Tilt",
)
BOTTOM_WATER_CORRECTED = Condition(Field.corr_SUR_flag, (PRESENT_CORRECTED,))
TILT_IS_CORRECTED = Condition(Field.corr_T_flag, (TILT_CORRECTED,))

LOCATION = Criterion(
    "probe-tc.location",
    "Conductivity location",
    Classes(
        (Field.tc_location,),
        (
            Group(0.0, (ACTUAL_LOCATION,)),
            Group(-0.1, (OTHER_LOCATION,)),
            Group(-0.2, (LITERATURE_OR_UNSPECIFIED,)),
        ),
        unmatched_marked=False,
    ),
    "Table 2, Localization",
)
SATURATION = Criterion(
    "probe-tc.saturation",
    "Saturation, method, source and location together",
    Cases(
        (
            Case(
                0.1,
                {
                    Field.tc_saturation: (SATURATED_IN_SITU,),
                    Field.tc_method: (PROBE_PULSE,),
                    Field.tc_source: (IN_SITU_PROBE,),
                },
            ),
            Case(
                0.0,
                {
                    Field.tc_saturation: (RECOVERED, SATURATED_MEASURED),
                    Field.tc_method: (PROBE_PULSE,),
                    Field.tc_source: (IN_SITU_PROBE,),
                },
            ),
            Case(
                0.0,
                {Field.tc_saturation: (RECOVERED, SATURATED_MEASURED)},
                every={Field.tc_method: LABORATORY_METHODS},
            ),
            Case(
                -0.1,
                {Field.tc_saturation: (SATURATED_CALCULATED,)},
                every={Field.tc_method: LABORATORY_METHODS},
            ),
            Case(
                -0.2,
                {Field.tc_saturation: DRY_UNSPECIFIED_OR_OTHER},
                every={Field.tc_method: LABORATORY_METHODS},
            ),
            Case(
                -0.1,
                {
                    Field.tc_method: ESTIMATED_FROM_LITERATURE,
                    Field.tc_location: (LITERATURE_OR_UNSPECIFIED,),
                },
            ),
            Case(-0.2, {Field.tc_method: ESTIMATED_FROM_OTHER}),
        )
    ),
    "Table 2, Source type and saturation",
)
NUMBER = Criterion(
    "probe-tc.number",
    "Number of conductivity measurements",
    Bands(
        Field.tc_number,
        (Band(0.0, 3), Band(-0.1, 1), Band(-0.2)),
        left_out_when={Field.tc_location: (LITERATURE_OR_UNSPECIFIED,)},
    ),
    "Table 2, Number of conductivities",
)
CONDITIONS = Criterion(
    "probe-tc.pT",
    "pT conditions and method",
    Cases(
        (
            Case(
                0.1,
                {
                    Field.tc_pT_conditions: (ACTUAL_IN_SITU,),
                    Field.tc_method: (PROBE_PULSE,),
                },
            ),
            Case(0.0, {Field.tc_pT_conditions: FULL_IN_SITU}),
            Case(-0.1, {Field.tc_pT_conditions: PARTIAL_IN_SITU}),
            Case(-0.2, {Field.tc_pT_conditions: AMBIENT_OR_UNSPECIFIED}),
        )
    ),
    "Table 2, pT conditions",
)

T_CRITERIA = (PENETRATION, RECORDINGS, WATER_DEPTH, TILT)
TC_CRITERIA = (LOCATION, SATURATION, NUMBER, CONDITIONS)


class ProbeRules(RuleSet):
    """Score the children explored by probing: the T-score and the TC-score.

    A field that holds several values is scored value by value and the poorest counts
    (docs/reference/quality-scheme/index.md, "Several values in one field"). A tilt
    correction waives the tilt criterion and a bottom-water correction waives the water
    depth, in the T-score but not in the own T-score.
    """

    criteria = (*T_CRITERIA, *TC_CRITERIA)
    waivers = {
        WATER_DEPTH.identifier: BOTTOM_WATER_CORRECTED,
        TILT.identifier: TILT_IS_CORRECTED,
    }

    def scores(self) -> RuleScores:
        """Score every child, each criterion once.

        The conductivity reads nothing from the child, so the own TC-score is the
        TC-score. See docs/reference/quality-scheme/probe-sensing.md, "T-score" and
        "TC-score", and docs/reference/quality-scheme/index.md, "Scores of a child and
        of its measurements".

        Returns:
            The four scores and their marks for each child.
        """
        t, own_t = self.penalties(T_CRITERIA)
        tc, own_tc = self.penalties(TC_CRITERIA)
        return RuleScores(
            t=Score.total(t, self.routed),
            tc=Score.total(tc, self.routed),
            own_t=Score.total(own_t, self.routed),
            own_tc=Score.total(own_tc, self.routed),
        )
