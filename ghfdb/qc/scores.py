"""The scores of the children of a dataset under the quality scheme."""

import pandas

from ghfdb.qc.rules import BOREHOLE, EXPLORATION_METHOD, PROBE_SENSING
from ghfdb.qc.scheme import Inputs, Terms

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
