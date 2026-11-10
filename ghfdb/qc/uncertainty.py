"""The U-score: the grade of the uncertainty of a heat-flow value."""

from dataclasses import dataclass

import pandas

from ghfdb.fields import Field
from ghfdb.qc.inputs import Inputs
from ghfdb.qc.penalties import Band

# The coefficient of variation is rounded to this many places, before it is graded.
COEFFICIENT_DECIMALS = 6
# The class of a coefficient, in percent: U4 above 25, U3 above 15, U2 from 5, else U1.
COEFFICIENT_CLASSES = (Band(4, 25), Band(3, 15), Band(2, 5, inclusive=True), Band(1))


@dataclass(frozen=True)
class UScore:
    """Grade the uncertainty of each child's heat-flow value from ``U1`` to ``U4``.

    Attributes:
        inputs: The scored fields of the children.
    """

    inputs: Inputs

    def coefficients(self) -> pandas.Series:
        """Find the coefficient of variation of every pair of value and uncertainty.

        The coefficient is ``|C2| / |C1| * 100`` rounded to six places, so the sign of
        either number is ignored (docs/reference/quality-scheme/u-score.md, "The
        coefficient of variation").

        Returns:
            One row for each pair of a value and an uncertainty of a child, under the
            child's index. It is NaN when either number is empty or zero.
        """
        pairs = Inputs.combine(
            {
                "value": self.inputs.numbers(Field.qc),
                "uncertainty": self.inputs.numbers(Field.qc_uncertainty),
            }
        )
        pairs = pairs.abs().where(pairs.ne(0))
        return (pairs["uncertainty"] / pairs["value"] * 100).round(COEFFICIENT_DECIMALS)

    def grades(self) -> pandas.Series:
        """Grade each child.

        A coefficient below 5 % is ``U1``, up to and including 15 % ``U2``, up to and
        including 25 % ``U3`` and above that ``U4``. The grade is ``Ux`` when either
        number is empty or zero, and has no missing-information mark
        (docs/reference/quality-scheme/u-score.md, "The coefficient of variation"
        and "Empty, zero and unspecified"). A child with several values takes its
        poorest pair.

        Returns:
            ``U1`` to ``U4`` or ``Ux`` for each child, in the order of the children.
        """
        coefficient = self.coefficients()
        classes = Band.select(COEFFICIENT_CLASSES, coefficient, 0)
        grade = pandas.Series(classes, index=coefficient.index).where(
            coefficient.notna(), 0
        )
        poorest = (
            grade.groupby(level=0, sort=False)
            .max()
            .reindex(self.inputs.index, fill_value=0)
        )
        return ("U" + poorest.astype(str)).where(poorest > 0, "Ux").astype("string")
