"""The U-score: the grade of the uncertainty of a heat-flow value."""

import pandas

from ghfdb.qc.scheme import Inputs

DECIMALS = 6
U2_FROM = 5.0
U3_ABOVE = 15.0
U4_ABOVE = 25.0


class UScore:
    """Grade the uncertainty of each child's heat-flow value from ``U1`` to ``U4``.

    Args:
        inputs: The scored fields of the children.

    Attributes:
        inputs: The scored fields of the children.
    """

    def __init__(self, inputs: Inputs) -> None:
        self.inputs = inputs

    def coefficients(self) -> pandas.Series:
        """Find the coefficient of variation of every pair of value and uncertainty.

        The coefficient is ``|C2| / |C1| * 100`` rounded to six places, so the sign of
        either number is ignored (docs/reference/quality-scheme/u-score.md, "The
        coefficient of variation").

        Returns:
            One row for each pair of a ``C1`` and a ``C2`` of a child, under the
            child's index. It is NaN when either number is empty or zero.
        """
        pairs = pandas.DataFrame({"C1": self.inputs.numbers["C1"]}).join(
            self.inputs.numbers["C2"]
        )
        pairs = pairs.abs().where(pairs.ne(0))
        return (pairs["C2"] / pairs["C1"] * 100).round(DECIMALS)

    def scores(self) -> pandas.Series:
        """Grade each child.

        A coefficient below 5 % is ``U1``, up to and including 15 % ``U2``, up to and
        including 25 % ``U3`` and above that ``U4``. The score is ``Ux`` when either
        number is empty or zero, and has no missing-information mark
        (docs/reference/quality-scheme/u-score.md, "The coefficient of variation"
        and "Empty, zero and unspecified"). A child with several values takes its
        poorest pair.

        Returns:
            ``U1`` to ``U4`` or ``Ux`` for each child, in the order of the children.
        """
        coefficient = self.coefficients()
        grade = (
            (coefficient >= U2_FROM).astype(int)
            + (coefficient > U3_ABOVE)
            + (coefficient > U4_ABOVE)
            + 1
        ).where(coefficient.notna(), 0)
        poorest = (
            grade.groupby(level=0, sort=False)
            .max()
            .reindex(self.inputs.index, fill_value=0)
        )
        return ("U" + poorest.astype(str)).where(poorest > 0, "Ux").astype("string")
