"""What the quality scheme says: its domains, its criteria and its grades.

The criteria are declared in ``probe`` and ``borehole``, the domains in ``domains``, the
concepts both name in ``groups`` and the grades in ``grades``. This module lists the
criteria that are tables by the identifier the worked examples use.
"""

from ghfdb.qc.engine.tables import Criterion, Table
from ghfdb.qc.scheme.borehole import BoreholeAndMine
from ghfdb.qc.scheme.probe import ProbeSensing

CRITERIA: dict[str, Criterion[Table]] = {
    criterion.identifier: criterion
    for domain in (ProbeSensing, BoreholeAndMine)
    for criterion in domain.declared()
}
