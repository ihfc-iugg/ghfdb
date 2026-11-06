"""The scores of the children of a dataset under the quality scheme."""

import pandas

from ghfdb.qc.rules import BOREHOLE, EXPLORATION_METHOD, PROBE_SENSING
from ghfdb.qc.scheme import (
    FLAG_FIELDS,
    NOT_RECOGNIZED,
    PRESENT_CORRECTED,
    PRESENT_NOT_CORRECTED,
    PRESENT_NOT_SIGNIFICANT,
    Inputs,
    Terms,
)

PROBE_RULES = "probe sensing"
BOREHOLE_RULES = "borehole and mine"


class Scores:
    """Routing and perturbation flags of the children of a dataset.

    Args:
        inputs: The scored fields of the children.
        terms: The terms the scheme's concepts resolve to.

    Attributes:
        inputs: The scored fields of the children.
        terms: The terms the scheme's concepts resolve to.
    """

    def __init__(self, inputs: Inputs, terms: Terms) -> None:
        self.inputs = inputs
        self.terms = terms

    def routing(self) -> pandas.Series:
        """Choose the set of rules that scores each child.

        The exploration method decides, as in "Which rules score a child" of the
        overview of the quality scheme (docs/reference/quality-scheme/index.md).

        Returns:
            ``probe sensing`` or ``borehole and mine`` for each child, in the order of
            the children, and ``<NA>`` where the method selects no rules because it
            is other, unspecified or empty.
        """
        methods = self.inputs.first(self.inputs.concepts[EXPLORATION_METHOD])
        rules = pandas.Series(pandas.NA, index=methods.index, dtype="string")
        rules = rules.mask(methods.isin(PROBE_SENSING.concepts), PROBE_RULES)
        return rules.mask(methods.isin(BOREHOLE.concepts), BOREHOLE_RULES)

    def flags(self) -> pandas.Series:
        """Write the seven perturbation flags of each child.

        The characters are in the order S E T P V C R, from the correction fields C13
        to C19: the upper-case letter for present and corrected, the lower-case letter
        for present and not corrected, ``X`` for present and not significant, ``x`` for
        not recognised, and ``-`` for unspecified, empty or a term the field does not
        allow (docs/reference/quality-scheme/perturbation-flags.md, "How each flag is
        written").

        Returns:
            The flags of each child, in the order of the children.
        """
        flags = pandas.Series("", index=self.inputs.index, dtype="string")
        for code, letter in zip(FLAG_FIELDS, "SETPVCR", strict=True):
            characters = {
                PRESENT_CORRECTED: letter,
                PRESENT_NOT_CORRECTED: letter.lower(),
                PRESENT_NOT_SIGNIFICANT: "X",
                NOT_RECOGNIZED: "x",
            }
            state = self.inputs.first(self.inputs.concepts[code])
            flags = flags + state.map(characters).fillna("-").astype("string")
        return flags
