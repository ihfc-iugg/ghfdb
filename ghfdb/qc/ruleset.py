"""A set of rules: the criteria that score a child's gradient and conductivity.

A set of rules declares its criteria, and what is read besides them, as class
attributes. The fields and concepts it reads, and the penalties of its criteria for a
child and for a measurement on its own, follow from those declarations.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, ClassVar

import numpy

from ghfdb.qc.inputs import Inputs
from ghfdb.qc.penalties import Criterion, Penalty, Score
from ghfdb.qc.rules import Condition


@dataclass(frozen=True)
class RuleScores:
    """The scores a set of rules gives every child.

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
class RuleSet:
    """The children one set of rules scores.

    A subclass lists in ``criteria`` every criterion its scores add up, and may declare:

    * ``waivers``, by the identifier of a criterion: the correction that, when a child
      has it, leaves the criterion out of the child's score.
    * ``stand_ins``, by the identifier of a criterion: the criterion that scores a
      measurement on its own in its place, where the criterion needs the child.
    * ``conditions`` and ``extra_fields``: what the code of the subclass reads that no
      criterion names.

    Attributes:
        inputs: The scored fields of the children.
        routed: Whether the rules score each child, in the order of the children: the
            child is routed to them and has a field they read filled.
        criteria: The criteria of the rules.
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
        """List every criterion the rules declare, the stand-ins included.

        Returns:
            The criteria, then the stand-ins.
        """
        return (*cls.criteria, *cls.stand_ins.values())

    @classmethod
    def corrections(cls) -> tuple[Condition, ...]:
        """List every condition the rules read besides those of the criteria.

        Returns:
            The conditions of the waivers, then the other conditions.
        """
        return (*cls.waivers.values(), *cls.conditions)

    @classmethod
    def reads(cls) -> tuple[str, ...]:
        """List the fields the rules read.

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
    def concepts(cls) -> tuple[tuple[str, str], ...]:
        """List the concepts the rules name, with their fields.

        Returns:
            The concepts of the criteria and of the conditions, each once.
        """
        criteria, corrections = cls.declared(), cls.corrections()
        return tuple(
            dict.fromkeys(
                (
                    *(pair for criterion in criteria for pair in criterion.concepts()),
                    *(
                        (condition.field, uri)
                        for condition in corrections
                        for uri in condition.concepts
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
        first = self.inputs.first(self.inputs.concepts(correction.field))
        return first.isin(correction.concepts).to_numpy(dtype=bool)

    def penalties(
        self, criteria: Sequence[Criterion[Any]]
    ) -> tuple[list[Penalty], list[Penalty]]:
        """Score each criterion for the child and for a measurement on its own.

        Each criterion is scored once. A waiver leaves the criterion out of the child's
        penalty, and a stand-in replaces it in the measurement's.

        Args:
            criteria: The criteria to score, which the rules declare.

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
