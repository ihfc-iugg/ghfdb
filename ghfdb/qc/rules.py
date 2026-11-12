"""The cross-field rules: what a child's fields must say together.

The field schema checks each field on its own. A cross-field rule relates two or more
fields of the same child, for example "a child explored by drilling has its interval
bottom filled". Every rule is declared here, in Python, and listed in ``RULES``, which
``DatasetCheck`` applies after the field check. Each broken rule is one line of kind
``rule`` in the problem table, with the rule's identifier in ``rule`` and the field
that decided the rule applies in ``related``.

A rule names the vocabulary values it needs by their concept, ``concepts.tc_source
["core-samples"]`` in ``ghfdb.vocabularies``, never by their term. ``DatasetCheck``
turns each concept into the term the field accepts, using the vocabularies the field
schema was built from, and refuses a concept the field does not accept. A collection of
the field's scheme stands for its members.

There are two kinds of rule:

* ``RequiredWhen``: a child whose exploration method belongs to a domain has every field
  that is mandatory for that domain only filled. The fields are read from the field
  schema.
* ``AllowedWhen``: when one field holds a given concept, or any of several fields
  holds one, another field may hold only a given concept.

To add a rule of an existing kind, write its ``Example`` and add it to ``RULES``, with a
new identifier that is never reused. To add a rule of a new kind:

1. Subclass ``Rule`` and add the fields the kind needs.
2. Implement ``fields(schema)``, listing the condition field first.
3. Implement ``concepts()``, listing each ``(field code, concept)`` the rule names, so
   the check can resolve them to terms on construction.
4. Implement ``problems(check)``, working on whole columns, and build its lines with
   ``check.rule_lines``. Use ``check.holds`` to find the children a condition holds for.
5. Implement ``diagram(schema, resolved)``, returning Mermaid flowchart text with quoted
   labels that name the terms the rule applies to, read from ``resolved``.

Nothing else changes: the check only calls those methods.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from functools import reduce
from typing import TYPE_CHECKING, Any

import pandas
from frictionless import Schema
from rdflib import URIRef

from ghfdb.fields import Field
from ghfdb.fields.schema import FieldConcepts
from ghfdb.vocabularies import concepts

if TYPE_CHECKING:
    from ghfdb.qc.check import DatasetCheck

EXPLORATION_METHOD = Field.explo_method
METHOD = concepts.explo_method
LOCATION = concepts.tc_location
SOURCE = concepts.tc_source
TEMPERATURE = concepts.T_method_top
CONDUCTIVITY = concepts.tc_method


@dataclass(frozen=True)
class Condition:
    """A field and the concepts that make a rule apply, or that it may then hold.

    Attributes:
        field: The code of the field.
        concepts: The concepts, or collections of the field's scheme.
    """

    field: str
    concepts: tuple[URIRef, ...]


@dataclass(frozen=True)
class Domain:
    """A set of exploration methods whose children share the mandatory fields.

    Attributes:
        code: The domain in the field schema's ``domain`` lists: ``B`` for borehole and
            mine data, ``S`` for probe sensing.
        field: The code of the field the exploration method is read from.
        concepts: The exploration methods in the domain.
        description: What a child of the domain is, as the end of "the exploration
            method is ...".
        rules: The name of the set of quality-scheme rules that score a child of the
            domain.
    """

    code: str
    field: str
    concepts: tuple[URIRef, ...]
    description: str
    rules: str

    @property
    def condition(self) -> Condition:
        """The condition that a child belongs to the domain."""
        return Condition(self.field, self.concepts)


BOREHOLE = Domain(
    "B",
    EXPLORATION_METHOD,
    (
        METHOD.drilling,
        METHOD["drilling-clustering"],
        METHOD.mining,
        METHOD.tunneling,
        METHOD.indirect,
    ),
    "a borehole and mine method",
    "borehole and mine",
)
PROBE_SENSING = Domain(
    "S",
    EXPLORATION_METHOD,
    (
        METHOD["probing-onshore"],
        METHOD["probing-offshore"],
        METHOD["probing-clustering"],
    ),
    "a probe-sensing method",
    "probe sensing",
)


@dataclass(frozen=True)
class Example:
    """A worked example of a rule: a child that breaks it.

    Attributes:
        values: The values of the fields the rule reads, by field code. A vocabulary
            value is its concept, an empty cell is None.
        expected: The codes of the fields the rule reports, in the order of the
            field schema.
    """

    values: Mapping[str, Any]
    expected: tuple[str, ...]

    def concepts(self) -> tuple[tuple[str, URIRef], ...]:
        """List the concepts the example's values name.

        Returns:
            Each ``(field code, concept)``.
        """
        return tuple(
            (code, value)
            for code, value in self.values.items()
            if isinstance(value, URIRef)
        )


@dataclass(frozen=True)
class Rule:
    """A rule that relates several fields of a child.

    Attributes:
        identifier: The rule's name, never changed or reused.
        statement: What the rule says, in a sentence.
        source: The source key of what the rule comes from, as in the field schema.
        reasoning: Why the rule holds.
        example: A child that breaks the rule.
    """

    identifier: str
    statement: str
    source: str
    reasoning: str
    example: Example

    def fields(self, schema: Schema) -> tuple[str, ...]:
        """List every field the rule relates.

        Args:
            schema: The field schema.

        Returns:
            The field codes, the condition's field first.
        """
        raise NotImplementedError

    def concepts(self) -> tuple[tuple[str, URIRef], ...]:
        """List the concepts the rule and its example name.

        Returns:
            Each ``(field code, concept)``.
        """
        raise NotImplementedError

    def problems(self, check: DatasetCheck) -> pandas.DataFrame:
        """Find the children that break the rule.

        Args:
            check: The check, which holds the data, the schema and the concepts.

        Returns:
            The lines of kind ``rule`` for the children that break the rule.
        """
        raise NotImplementedError

    def diagram(self, schema: Schema, resolved: Mapping[str, FieldConcepts]) -> str:
        """Draw the rule.

        Args:
            schema: The field schema.
            resolved: The concepts the rule names, resolved for their fields, by field
                code.

        Returns:
            Mermaid flowchart text.
        """
        raise NotImplementedError

    @staticmethod
    def label(schema: Schema, code: str) -> str:
        """Name a field for a diagram, with its title.

        Args:
            schema: The field schema.
            code: The field's code.

        Returns:
            The code and the title.
        """
        return f"{code} {schema.get_field(code).title}"


@dataclass(frozen=True)
class RequiredWhen(Rule):
    """A child in a domain has every field mandatory for that domain only filled.

    Attributes:
        domain: The domain, and the exploration methods that put a child in it.
    """

    domain: Domain

    def required(self, schema: Schema) -> tuple[str, ...]:
        """Read the fields the domain requires from the field schema.

        Args:
            schema: The field schema.

        Returns:
            The codes of the fields mandatory in this domain only, in schema order.
        """
        return tuple(
            field.name
            for field in schema.fields
            if field.custom["obligation"] == "M"
            and set(field.custom["domain"]) == {self.domain.code}
        )

    def fields(self, schema: Schema) -> tuple[str, ...]:
        """List the exploration method field and the fields the domain requires."""
        return (self.domain.field, *self.required(schema))

    def problems(self, check: DatasetCheck) -> pandas.DataFrame:
        """Report each required field that is empty for a child in the domain."""
        nothing = pandas.Series(dtype="string")
        field = check.schema.get_field(self.domain.field)
        found = [check.rule_lines(self, field, nothing, nothing)]
        applies = check.holds(self.domain.condition)
        if applies.any():
            related = check.found(self.domain.condition)
            for code in self.required(check.schema):
                if code in check.data.columns:
                    column = check.data[code].astype("string")
                    empty = column[applies & check.blank(column)]
                    field = check.schema.get_field(code)
                    found.append(check.rule_lines(self, field, empty, related))
        return pandas.concat(found)

    def concepts(self) -> tuple[tuple[str, URIRef], ...]:
        """List the exploration-method concepts of the domain, then the example's."""
        named = [(self.domain.field, concept) for concept in self.domain.concepts]
        return (*named, *self.example.concepts())

    def diagram(self, schema: Schema, resolved: Mapping[str, FieldConcepts]) -> str:
        """Draw the domain condition leading to each field it requires."""
        when = self.label(schema, self.domain.field)
        lines = [
            "flowchart LR",
            f'    when["{when} is {self.domain.description}"]',
        ]
        for index, code in enumerate(self.required(schema)):
            lines.append(
                f'    when --> need{index}["{self.label(schema, code)} filled"]'
            )
        return "\n".join(lines)


@dataclass(frozen=True)
class AllowedWhen(Rule):
    """When a field holds given concepts, another may hold only given concepts.

    Attributes:
        when: The field and the concepts that make the rule apply.
        then: The field and the only concepts it may then hold.
        alternatives: Further fields and concepts, any one of which makes the rule
            apply as well.
    """

    when: Condition
    then: Condition
    alternatives: tuple[Condition, ...] = ()

    def conditions(self) -> tuple[Condition, ...]:
        """List every condition that makes the rule apply.

        Returns:
            ``when``, then the alternatives.
        """
        return (self.when, *self.alternatives)

    def fields(self, schema: Schema) -> tuple[str, ...]:
        """Name the condition fields, then the field the rule limits."""
        return (*(c.field for c in self.conditions()), self.then.field)

    def problems(self, check: DatasetCheck) -> pandas.DataFrame:
        """Report each value the field may not hold when the condition holds.

        A child whose limited field holds a value not in the vocabulary is skipped: that
        cell already has a field problem.

        Args:
            check: The check, which holds the data, the schema and the concepts.

        Returns:
            One line of kind ``rule`` for each value the limited field may not hold.
        """
        nothing = pandas.Series(dtype="string")
        field = check.schema.get_field(self.then.field)
        found = [check.rule_lines(self, field, nothing, nothing)]
        held = [check.holds(condition) for condition in self.conditions()]
        applies = pandas.concat(held, axis=1).any(axis=1)
        if applies.any() and field.name in check.data.columns:
            column = check.data[field.name].astype("string")
            values = check.each_value(field, column[applies & ~check.blank(column)])
            allowed = check.concepts[field.name].terms_for(self.then.concepts)
            published = values.isin(field.constraints.get("enum", []))
            whole = published.groupby(level=0).transform("all")
            wrong = values[whole & ~values.isin(allowed)]
            related = reduce(
                pandas.Series.combine_first,
                [
                    check.found(condition).where(holds)
                    for condition, holds in zip(self.conditions(), held, strict=True)
                    if holds.any()
                ],
            )
            found.append(check.rule_lines(self, field, wrong, related))
        return pandas.concat(found)

    @staticmethod
    def named(condition: Condition, resolved: Mapping[str, FieldConcepts]) -> str:
        """Name the terms of a condition for a diagram.

        Args:
            condition: A field and its concepts.
            resolved: The concepts resolved for their fields, by field code.

        Returns:
            The terms, joined with " or ".
        """
        return " or ".join(resolved[condition.field].terms_for(condition.concepts))

    def concepts(self) -> tuple[tuple[str, URIRef], ...]:
        """List the conditions' concepts, the allowed ones, then the example's."""
        named = [
            *((c.field, concept) for c in self.conditions() for concept in c.concepts),
            *((self.then.field, concept) for concept in self.then.concepts),
        ]
        return (*named, *self.example.concepts())

    def diagram(self, schema: Schema, resolved: Mapping[str, FieldConcepts]) -> str:
        """Draw the condition leading to the limit on the other field."""
        when = " or ".join(
            f"{self.label(schema, c.field)} is {self.named(c, resolved)}"
            for c in self.conditions()
        )
        then = self.label(schema, self.then.field)
        return "\n".join(
            [
                "flowchart LR",
                f'    when["{when}"]',
                f'    then["{then} must be {self.named(self.then, resolved)}"]',
                "    when --> then",
            ]
        )


CF_1 = RequiredWhen(
    identifier="CF-1",
    statement=(
        "A child explored through a borehole, a mine or a tunnel, or estimated "
        "indirectly, has every field mandatory for borehole and mine data filled."
    ),
    source="fuchs-2023-table-4",
    reasoning=(
        "Table 4 of Fuchs et al. (2023) marks these fields mandatory for borehole and "
        "mine data only, so a child of that domain must fill them. Which exploration "
        "methods belong to the domain is set out with the rules, and is open to "
        "confirmation by the data assessment team."
    ),
    example=Example(
        {Field.explo_method: METHOD.drilling, Field.q_bottom: None}, (Field.q_bottom,)
    ),
    domain=BOREHOLE,
)
CF_2 = RequiredWhen(
    identifier="CF-2",
    statement=(
        "A child explored by probing has every field mandatory for probe sensing "
        "filled."
    ),
    source="fuchs-2023-table-4",
    reasoning=(
        "Table 4 of Fuchs et al. (2023) marks these fields mandatory for probe sensing "
        "only, so a child of that domain must fill them. Which exploration methods "
        "belong to the domain is set out with the rules, and is open to confirmation "
        "by the data assessment team."
    ),
    example=Example(
        {Field.explo_method: METHOD["probing-onshore"], Field.probe_penetration: None},
        (Field.probe_penetration,),
    ),
    domain=PROBE_SENSING,
)
CF_3 = AllowedWhen(
    identifier="CF-3",
    statement=(
        "A thermal conductivity location of literature or unspecified is allowed only "
        "when the thermal conductivity source is assumed from literature."
    ),
    source="fuchs-2023-appendix-a",
    reasoning=(
        "Appendix A of Fuchs et al. (2023) allows the location literature or "
        "unspecified only if the source is assumed from literature: conductivity "
        "measured on samples or in situ was measured somewhere, so its location is "
        "known."
    ),
    example=Example(
        {
            Field.tc_location: LOCATION.literature,
            Field.tc_source: SOURCE["core-samples"],
        },
        (Field.tc_source,),
    ),
    when=Condition(Field.tc_location, (LOCATION.literature,)),
    then=Condition(Field.tc_source, (SOURCE["assumed-from-literature"],)),
)

CF_4 = AllowedWhen(
    identifier="CF-4",
    statement=(
        "A child whose temperature method at the top or at the bottom is the enhanced "
        "geothermal response test has the thermal conductivity method probe - pulse "
        "technique."
    ),
    source="fuchs-2025-template-2026-03",
    reasoning=(
        "Section 6.1 of the description of version 2026.03 of the submission template "
        "asks that, when the enhanced geothermal response test is used as the "
        "temperature method, the thermal conductivity method is the probe pulse "
        "technique, so that thermal conductivity is reported consistently."
    ),
    example=Example(
        {
            Field.T_method_top: TEMPERATURE.EGRT,
            Field.tc_method: CONDUCTIVITY.pointSource,
        },
        (Field.tc_method,),
    ),
    when=Condition(Field.T_method_top, (TEMPERATURE.EGRT,)),
    then=Condition(Field.tc_method, (CONDUCTIVITY.probePulse,)),
    alternatives=(Condition(Field.T_method_bottom, (TEMPERATURE.EGRT,)),),
)

RULES: tuple[Rule, ...] = (CF_1, CF_2, CF_3, CF_4)
