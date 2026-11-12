"""The two domains of the quality scheme: which exploration methods each one scores.

A domain is one of the collections of exploration methods that the vocabulary publishes.
"""

from ghfdb.fields import Field
from ghfdb.qc.engine.rule_kinds import Domain
from ghfdb.vocabularies import concepts

EXPLORATION_METHOD = Field.explo_method

BOREHOLE = Domain(
    "B",
    EXPLORATION_METHOD,
    (concepts.explo_method["borehole-and-mine"],),
    "a borehole and mine method",
    "borehole and mine",
)
PROBE_SENSING = Domain(
    "S",
    EXPLORATION_METHOD,
    (concepts.explo_method["probe-sensing"],),
    "a probe-sensing method",
    "probe sensing",
)
