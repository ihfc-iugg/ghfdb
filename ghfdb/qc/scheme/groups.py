"""Groups of concepts that the probe-sensing and the borehole criteria both name."""

from ghfdb.vocabularies import concepts

TC_PT_CONDITIONS = concepts.tc_pT_conditions
TC_SATURATION = concepts.tc_saturation

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
