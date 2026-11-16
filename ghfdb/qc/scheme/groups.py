"""Groups of concepts that the probe-sensing and the borehole criteria both name."""

from ghfdb.vocabularies import concepts

TC_PT_CONDITIONS = concepts.tc_pT_conditions
TC_SATURATION = concepts.tc_saturation

DRY_UNSPECIFIED_OR_OTHER = (
    TC_SATURATION["dry-measured"],
    TC_SATURATION.unspecified,
    TC_SATURATION.other,
)
FULL_IN_SITU = (TC_PT_CONDITIONS["replicated-pT"], TC_PT_CONDITIONS["corrected-pT"])
PARTIAL_IN_SITU = (
    TC_PT_CONDITIONS["replicated-p"],
    TC_PT_CONDITIONS["corrected-p"],
    TC_PT_CONDITIONS["replicated-T"],
    TC_PT_CONDITIONS["corrected-T"],
)
AMBIENT_OR_UNSPECIFIED = (TC_PT_CONDITIONS.ambient, TC_PT_CONDITIONS.unspecified)
