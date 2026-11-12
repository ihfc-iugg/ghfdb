"""Every criterion of the quality scheme that is a table.

The criteria are declared in ``probe`` and ``borehole``. This module lists them by the
identifier the worked examples use.
"""

from ghfdb.qc.borehole import BoreholeAndMine
from ghfdb.qc.engine.tables import Criterion, Table
from ghfdb.qc.probe import ProbeSensing

CRITERIA: dict[str, Criterion[Table]] = {
    criterion.identifier: criterion
    for rules in (ProbeSensing, BoreholeAndMine)
    for criterion in rules.declared()
}
