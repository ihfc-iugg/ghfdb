"""The kinds of cross-field rule, and what they are made of.

A rule relates two or more fields of the same child, for example "a child explored by
drilling has its interval bottom filled". The rules themselves are declared in
``ghfdb.qc.rules``. This module holds the kinds a rule can be and the pieces they are
declared with: a ``Condition`` on a field, a ``Domain`` of exploration methods and an
``Example`` of a child that breaks the rule.

There are two kinds of rule:

* ``RequiredWhen``: a child whose exploration method belongs to a domain has every field
  that is mandatory for that domain only filled. The fields are read from the field
  schema.
* ``AllowedWhen``: when one field holds a given concept, or any of several fields
  holds one, another field may hold only a given concept.

To add a rule of a new kind:

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

from ghfdb.fields.schema import FieldConcepts

if TYPE_CHECKING:
    from ghfdb.qc.check import DatasetCheck


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
