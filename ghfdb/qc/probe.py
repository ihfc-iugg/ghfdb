"""The probe-sensing rules.

They give the T-score of a gradient and the TC-score of a conductivity. The criteria are
declared here as tables (see ``penalties``), and the two corrections that waive a
criterion are declared beside them in ``ProbeRules``.
"""

from ghfdb.fields import Field
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
from ghfdb.vocabularies import concepts

CORR_SUR_FLAG = concepts.corr_SUR_flag
CORR_T_FLAG = concepts.corr_T_flag
TC_LOCATION = concepts.tc_location
TC_METHOD = concepts.tc_method
TC_PT_CONDITIONS = concepts.tc_pT_conditions
TC_SATURATION = concepts.tc_saturation
TC_SOURCE = concepts.tc_source

# Saturation and pT conditions that the borehole conductivity criteria name too.
DRY_UNSPECIFIED_OR_OTHER = (
    TC_SATURATION.dryMeasured,
    TC_SATURATION.unspecified,
    TC_SATURATION.other,
)
FULL_IN_SITU = (TC_PT_CONDITIONS.replicatedPT, TC_PT_CONDITIONS.correctedPT)
PARTIAL_IN_SITU = (
    TC_PT_CONDITIONS.replicatedP,
    TC_PT_CONDITIONS.correctedP,
    TC_PT_CONDITIONS.replicatedT,
    TC_PT_CONDITIONS.correctedT,
)
AMBIENT_OR_UNSPECIFIED = (
    TC_PT_CONDITIONS.recordedAmbient,
    TC_PT_CONDITIONS.unrecordedAmbient,
    TC_PT_CONDITIONS.unspecified,
)

LABORATORY_METHODS = (
    TC_METHOD.pointSource,
    TC_METHOD.lineSourceFull,
    TC_METHOD.lineSourceHalf,
    TC_METHOD.planeSourceFull,
    TC_METHOD.planeSourceHalf,
    TC_METHOD.laboratoryOther,
)
ESTIMATED_FROM_LITERATURE = (
    TC_METHOD.lithology,
    TC_METHOD.wellLogDeterministic,
    TC_METHOD.wellLogEmpirical,
)
ESTIMATED_FROM_OTHER = (
    TC_METHOD.waterContent,
    TC_METHOD.mineralComposition,
    TC_METHOD.chlorineContent,
    TC_METHOD.unspecified,
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
BOTTOM_WATER_CORRECTED = Condition(
    Field.corr_SUR_flag, (CORR_SUR_FLAG["present-corrected"],)
)
TILT_IS_CORRECTED = Condition(Field.corr_T_flag, (CORR_T_FLAG.tiltCorrected,))

LOCATION = Criterion(
    "probe-tc.location",
    "Conductivity location",
    Classes(
        (Field.tc_location,),
        (
            Group(0.0, (TC_LOCATION.actual,)),
            Group(-0.1, (TC_LOCATION.other,)),
            Group(-0.2, (TC_LOCATION.literature,)),
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
                    Field.tc_saturation: (TC_SATURATION.saturatedInSitu,),
                    Field.tc_method: (TC_METHOD.probePulse,),
                    Field.tc_source: (TC_SOURCE["insitu-probe"],),
                },
            ),
            Case(
                0.0,
                {
                    Field.tc_saturation: (
                        TC_SATURATION.recovered,
                        TC_SATURATION.saturatedMeasured,
                    ),
                    Field.tc_method: (TC_METHOD.probePulse,),
                    Field.tc_source: (TC_SOURCE["insitu-probe"],),
                },
            ),
            Case(
                0.0,
                {
                    Field.tc_saturation: (
                        TC_SATURATION.recovered,
                        TC_SATURATION.saturatedMeasured,
                    )
                },
                every={Field.tc_method: LABORATORY_METHODS},
            ),
            Case(
                -0.1,
                {Field.tc_saturation: (TC_SATURATION.saturatedCalculated,)},
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
                    Field.tc_location: (TC_LOCATION.literature,),
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
        left_out_when={Field.tc_location: (TC_LOCATION.literature,)},
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
                    Field.tc_pT_conditions: (TC_PT_CONDITIONS.actualInSitu,),
                    Field.tc_method: (TC_METHOD.probePulse,),
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
