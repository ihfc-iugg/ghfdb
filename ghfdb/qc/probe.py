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

# Saturation and pT conditions that the borehole conductivity criteria name too.
DRY_UNSPECIFIED_OR_OTHER = ("dryMeasured", "unspecified", "other")
FULL_IN_SITU = ("replicatedPT", "correctedPT")
PARTIAL_IN_SITU = ("replicatedP", "correctedP", "replicatedT", "correctedT")
AMBIENT_OR_UNSPECIFIED = ("recordedAmbient", "unrecordedAmbient", "unspecified")

LABORATORY_METHODS = (
    "pointSource",
    "lineSourceFull",
    "lineSourceHalf",
    "planeSourceFull",
    "planeSourceHalf",
    "laboratoryOther",
)
ESTIMATED_FROM_LITERATURE = ("lithology", "wellLogDeterministic", "wellLogEmpirical")
ESTIMATED_FROM_OTHER = (
    "waterContent",
    "mineralComposition",
    "chlorineContent",
    "unspecified",
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
BOTTOM_WATER_CORRECTED = Condition(Field.corr_SUR_flag, ("present-corrected",))
TILT_IS_CORRECTED = Condition(Field.corr_T_flag, ("tiltCorrected",))

LOCATION = Criterion(
    "probe-tc.location",
    "Conductivity location",
    Classes(
        (Field.tc_location,),
        (
            Group(0.0, ("actual",)),
            Group(-0.1, ("other",)),
            Group(-0.2, ("literature",)),
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
                    Field.tc_saturation: ("saturatedInSitu",),
                    Field.tc_method: ("probePulse",),
                    Field.tc_source: ("insitu-probe",),
                },
            ),
            Case(
                0.0,
                {
                    Field.tc_saturation: ("recovered", "saturatedMeasured"),
                    Field.tc_method: ("probePulse",),
                    Field.tc_source: ("insitu-probe",),
                },
            ),
            Case(
                0.0,
                {Field.tc_saturation: ("recovered", "saturatedMeasured")},
                every={Field.tc_method: LABORATORY_METHODS},
            ),
            Case(
                -0.1,
                {Field.tc_saturation: ("saturatedCalculated",)},
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
                    Field.tc_location: ("literature",),
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
        left_out_when={Field.tc_location: ("literature",)},
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
                    Field.tc_pT_conditions: ("actualInSitu",),
                    Field.tc_method: ("probePulse",),
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
