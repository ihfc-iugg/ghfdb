"""The scoring of one domain: its criteria for a gradient and a conductivity.

A domain's scoring declares its criteria, and what is read besides them, as class
attributes. The fields and concepts it reads, and the penalties of its criteria for a
child and for a measurement on its own, follow from those declarations.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, ClassVar

import numpy
from rdflib import URIRef

from ghfdb.qc.engine.inputs import Inputs
from ghfdb.qc.engine.rule_kinds import Condition
from ghfdb.qc.engine.tables import Criterion, Penalty, Score


@dataclass(frozen=True)
class DomainScores:
    """The scores the scoring of a domain gives every child.

    Attributes:
        t: The T-score, with the child's corrections applied.
        tc: The TC-score, with the child's corrections applied.
        own_t: The T-score of the gradient on its own, before the corrections apply.
        own_tc: The TC-score of the conductivity on its own.
    """

    t: Score
    tc: Score
    own_t: Score
    own_tc: Score


@dataclass(frozen=True)
class DomainScoring:
    """The scoring of the children of one domain.

    A subclass lists in ``criteria`` every criterion its scores add up, and may declare:

    * ``waivers``, by the identifier of a criterion: the correction that, when a child
      has it, leaves the criterion out of the child's score.
    * ``stand_ins``, by the identifier of a criterion: the criterion that scores a
      measurement on its own in its place, where the criterion needs the child.
    * ``conditions`` and ``extra_fields``: what the code of the subclass reads that no
      criterion names.

    Attributes:
        inputs: The scored fields of the children.
        routed: Whether the scoring scores each child, in the order of the children:
            the child is routed to it and has a field it reads filled.
        criteria: The criteria of the scoring.
        waivers: The correction that waives each criterion, by identifier.
        stand_ins: The criterion that scores a measurement on its own in place of each
            criterion, by identifier.
        conditions: The conditions the code reads besides those of the waivers.
        extra_fields: The fields the code reads that no criterion or condition names.
    """

    inputs: Inputs
    routed: numpy.ndarray

    criteria: ClassVar[tuple[Criterion[Any], ...]] = ()
    waivers: ClassVar[Mapping[str, Condition]] = {}
    stand_ins: ClassVar[Mapping[str, Criterion[Any]]] = {}
    conditions: ClassVar[tuple[Condition, ...]] = ()
    extra_fields: ClassVar[tuple[str, ...]] = ()

    @classmethod
    def declared(cls) -> tuple[Criterion[Any], ...]:
        """List every criterion the scoring declares, the stand-ins included.

        Returns:
            The criteria, then the stand-ins.
        """
        return (*cls.criteria, *cls.stand_ins.values())

    @classmethod
    def corrections(cls) -> tuple[Condition, ...]:
        """List every condition the scoring reads besides those of the criteria.

        Returns:
            The conditions of the waivers, then the other conditions.
        """
        return (*cls.waivers.values(), *cls.conditions)

    @classmethod
    def reads(cls) -> tuple[str, ...]:
        """List the fields the scoring reads.

        Returns:
            The fields of the criteria, of the conditions and the extra fields, each
            once.
        """
        criteria, corrections = cls.declared(), cls.corrections()
        return tuple(
            dict.fromkeys(
                (
                    *(field for criterion in criteria for field in criterion.reads()),
                    *(condition.field for condition in corrections),
                    *cls.extra_fields,
                )
            )
        )

    @classmethod
    def concepts(cls) -> tuple[tuple[str, URIRef], ...]:
        """List the concepts the scoring names, with their fields.

        Returns:
            The concepts of the criteria and of the conditions, each once.
        """
        criteria, corrections = cls.declared(), cls.corrections()
        return tuple(
            dict.fromkeys(
                (
                    *(pair for criterion in criteria for pair in criterion.concepts()),
                    *(
                        (condition.field, concept)
                        for condition in corrections
                        for concept in condition.concepts
                    ),
                )
            )
        )

    def has(self, correction: Condition) -> numpy.ndarray:
        """Find the children that have a correction.

        Args:
            correction: The field of the correction and the concepts it must hold, read
                at the child's first value.

        Returns:
            Whether each child has the correction.
        """
        field = correction.field
        first = self.inputs.first(self.inputs.concepts(field))
        wanted = self.inputs.expand(field, correction.concepts)
        return first.isin(wanted).to_numpy(dtype=bool)

    def penalties(
        self, criteria: Sequence[Criterion[Any]]
    ) -> tuple[list[Penalty], list[Penalty]]:
        """Score each criterion for the child and for a measurement on its own.

        Each criterion is scored once. A waiver leaves the criterion out of the child's
        penalty, and a stand-in replaces it in the measurement's.

        Args:
            criteria: The criteria to score, which the scoring declares.

        Returns:
            The penalty of each criterion with the child's corrections applied, and the
            penalty of each on its own, in the order of ``criteria``.
        """
        child, alone = [], []
        for criterion in criteria:
            penalty = criterion.score(self.inputs)
            waiver = self.waivers.get(criterion.identifier)
            stand_in = self.stand_ins.get(criterion.identifier)
            child.append(
                penalty if waiver is None else penalty.waived(self.has(waiver))
            )
            alone.append(penalty if stand_in is None else stand_in.score(self.inputs))
        return child, alone
