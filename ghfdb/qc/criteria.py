"""Every criterion of the quality scheme that is a table.

The criteria are declared in ``probe`` and ``borehole``. This module lists them by the
identifier the worked examples use.
"""

from ghfdb.qc.borehole import BoreholeRules
from ghfdb.qc.penalties import Criterion, Table
from ghfdb.qc.probe import ProbeRules

CRITERIA: dict[str, Criterion[Table]] = {
    criterion.identifier: criterion
    for rules in (ProbeRules, BoreholeRules)
    for criterion in rules.declared()
}
