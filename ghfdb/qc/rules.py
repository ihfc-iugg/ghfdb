"""The cross-field rules: what a child's fields must say together.

The field schema checks each field on its own. A cross-field rule relates two or more
fields of the same child, for example "a child explored by drilling has its interval
bottom filled". Every rule is declared here, in Python, and listed in ``RULES``, which
``DatasetCheck`` applies after the field check. Each broken rule is one line of kind
``rule`` in the problem table, with the rule's identifier in ``rule`` and the field
that decided the rule applies in ``related``.

A rule names the vocabulary values it needs by the URI of their concept, never by
their term. ``DatasetCheck`` turns each URI into the term the field accepts, using the
vocabularies the field schema was built from, and refuses a URI the field does not
accept.

There are two kinds of rule:

* ``RequiredWhen``: a child whose exploration method belongs to a domain has every field
  that is mandatory for that domain only filled. The fields are read from the field
  schema.
* ``AllowedWhen``: when one field holds a given concept, another field may hold only a
  given concept.

To add a rule of an existing kind, write its ``Example`` and add it to ``RULES``, with a
new identifier that is never reused. To add a rule of a new kind:

1. Subclass ``Rule`` and add the fields the kind needs.
2. Implement ``fields(schema)``, listing the condition field first.
3. Implement ``concepts()``, listing each ``(field code, concept URI)`` the rule names,
   so the check can resolve them to terms on construction.
4. Implement ``problems(check)``, working on whole columns, and build its lines with
   ``check.rule_lines``. Use ``check.holds`` to find the children a condition holds for.
5. Implement ``diagram(schema)``, returning Mermaid flowchart text with quoted labels.

Nothing else changes: the check only calls those methods.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import pandas
from frictionless import Schema

if TYPE_CHECKING:
    from ghfdb.qc.check import DatasetCheck

VOCABULARIES = "https://w3id.org/ihfc-iugg/vocabularies"
EXPLORATION_METHODS = f"{VOCABULARIES}/exploration-methods"
CONDUCTIVITY_LOCATION = f"{VOCABULARIES}/conductivity-location"
CONDUCTIVITY_SOURCES = f"{VOCABULARIES}/conductivity-sources"

DRILLING = f"{EXPLORATION_METHODS}/drilling"
DRILLING_CLUSTERED = f"{EXPLORATION_METHODS}/drilling_clustering"
MINING = f"{EXPLORATION_METHODS}/mining"
TUNNELING = f"{EXPLORATION_METHODS}/tunneling"
INDIRECT = f"{EXPLORATION_METHODS}/indirect"
PROBING_ONSHORE = f"{EXPLORATION_METHODS}/probing_onshore"
PROBING_OFFSHORE = f"{EXPLORATION_METHODS}/probing_offshore"
PROBING_CLUSTERED = f"{EXPLORATION_METHODS}/probing_clustering"
LITERATURE_OR_UNSPECIFIED = f"{CONDUCTIVITY_LOCATION}/literature"
ASSUMED_FROM_LITERATURE = f"{CONDUCTIVITY_SOURCES}/assumed_from_literature"
CORE_SAMPLES = f"{CONDUCTIVITY_SOURCES}/core_samples"

EXPLORATION_METHOD = "P12"


@dataclass(frozen=True)
class Condition:
    """A field and the concepts that make a rule apply, or that it may then hold.

    Attributes:
        field: The code of the field.
        concepts: The URIs of the concepts.
    """

    field: str
    concepts: tuple[str, ...]


@dataclass(frozen=True)
class Domain:
    """A set of exploration methods whose children share the mandatory fields.

    Attributes:
        code: The domain in the field schema's ``domain`` lists: ``B`` for borehole and
            mine data, ``S`` for probe sensing.
        field: The code of the field the exploration method is read from.
        concepts: The URIs of the exploration methods in the domain.
    """

    code: str
    field: str
    concepts: tuple[str, ...]

    @property
    def condition(self) -> Condition:
        """The condition that a child belongs to the domain."""
        return Condition(self.field, self.concepts)


BOREHOLE = Domain(
    "B",
    EXPLORATION_METHOD,
    (DRILLING, DRILLING_CLUSTERED, MINING, TUNNELING, INDIRECT),
)
PROBE_SENSING = Domain(
    "S", EXPLORATION_METHOD, (PROBING_ONSHORE, PROBING_OFFSHORE, PROBING_CLUSTERED)
)


@dataclass(frozen=True)
class Example:
    """A worked example of a rule: a child that breaks it.

    Attributes:
        values: The values of the fields the rule reads, by field code. A vocabulary
            value is the URI of its concept, an empty cell is None.
        expected: The codes of the fields the rule reports, in the order of the
            field schema.
    """

    values: Mapping[str, Any]
    expected: tuple[str, ...]

    def concepts(self) -> tuple[tuple[str, str], ...]:
        """List the concepts the example's values name.

        Returns:
            Each ``(field code, concept URI)``.
        """
        return tuple(
            (code, value)
            for code, value in self.values.items()
            if isinstance(value, str) and value.startswith("https://")
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

    def concepts(self) -> tuple[tuple[str, str], ...]:
        """List the concepts the rule and its example name.

        Returns:
            Each ``(field code, concept URI)``.
        """
        raise NotImplementedError

    def problems(self, check: DatasetCheck) -> pandas.DataFrame:
        """Find the children that break the rule.

        Args:
            check: The check, which holds the data, the schema and the terms.

        Returns:
            The lines of kind ``rule`` for the children that break the rule.
        """
        raise NotImplementedError

    def diagram(self, schema: Schema) -> str:
        """Draw the rule.

        Args:
            schema: The field schema.

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

    def concepts(self) -> tuple[tuple[str, str], ...]:
        """List the exploration-method concepts of the domain, then the example's."""
        named = [(self.domain.field, uri) for uri in self.domain.concepts]
        return (*named, *self.example.concepts())

    def diagram(self, schema: Schema) -> str:
        """Draw the domain condition leading to each field it requires."""
        lines = [
            "flowchart LR",
            f'    when["{self.label(schema, self.domain.field)} is in the domain"]',
        ]
        for index, code in enumerate(self.required(schema)):
            lines.append(
                f'    when --> need{index}["{self.label(schema, code)} filled"]'
            )
        return "\n".join(lines)


@dataclass(frozen=True)
class AllowedWhen(Rule):
    """When one field holds given concepts, another may hold only given concepts.

    Attributes:
        when: The field and the concepts that make the rule apply.
        then: The field and the only concepts it may then hold.
    """

    when: Condition
    then: Condition

    def fields(self, schema: Schema) -> tuple[str, ...]:
        """Name the condition field, then the field the rule limits."""
        return (self.when.field, self.then.field)

    def problems(self, check: DatasetCheck) -> pandas.DataFrame:
        """Report each value the field may not hold when the condition holds."""
        nothing = pandas.Series(dtype="string")
        field = check.schema.get_field(self.then.field)
        found = [check.rule_lines(self, field, nothing, nothing)]
        applies = check.holds(self.when)
        if applies.any() and field.name in check.data.columns:
            column = check.data[field.name].astype("string")
            values = check.each_value(field, column[applies & ~check.blank(column)])
            allowed = [check.terms[field.name, uri] for uri in self.then.concepts]
            published = values.isin(field.constraints.get("enum", []))
            wrong = values[published & ~values.isin(allowed)]
            found.append(check.rule_lines(self, field, wrong, check.found(self.when)))
        return pandas.concat(found)

    def concepts(self) -> tuple[tuple[str, str], ...]:
        """List the condition's concepts, the allowed ones, then the example's."""
        named = [
            *((self.when.field, uri) for uri in self.when.concepts),
            *((self.then.field, uri) for uri in self.then.concepts),
        ]
        return (*named, *self.example.concepts())

    def diagram(self, schema: Schema) -> str:
        """Draw the condition leading to the limit on the other field."""
        when = self.label(schema, self.when.field)
        then = self.label(schema, self.then.field)
        return "\n".join(
            [
                "flowchart LR",
                f'    when["{when} holds a given value"]',
                f'    then["{then} holds only a given value"]',
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
        "methods belong to the domain is ruled in decision:004:D-1."
    ),
    example=Example({"P12": DRILLING, "C5": None}, ("C5",)),
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
        "belong to the domain is ruled in decision:004:D-1."
    ),
    example=Example({"P12": PROBING_ONSHORE, "C6": None}, ("C6",)),
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
        "Appendix A of Fuchs et al. (2023) describes this location as for conductivity "
        "taken from published values, so any other source contradicts it."
    ),
    example=Example({"C42": LITERATURE_OR_UNSPECIFIED, "C41": CORE_SAMPLES}, ("C41",)),
    when=Condition("C42", (LITERATURE_OR_UNSPECIFIED,)),
    then=Condition("C41", (ASSUMED_FROM_LITERATURE,)),
)

RULES: tuple[Rule, ...] = (CF_1, CF_2, CF_3)
