"""Render the rule reference from the cross-field rules at documentation build time."""

from collections.abc import Sequence
from functools import cache
from pathlib import Path
from typing import Any

from frictionless import Schema
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from rdflib import URIRef
from sphinx.application import Sphinx

from extensions.field_reference import FieldReference
from ghfdb.fields import load_schema
from ghfdb.fields.schema import FieldConcepts
from ghfdb.qc.check import Kind
from ghfdb.qc.rules import BOREHOLE, PROBE_SENSING, RULES, Domain, Rule
from ghfdb.vocabularies import Vocabularies

TEMPLATES = Path(__file__).parent / "templates"
PAGE = "reference/rules"


class RuleReference:
    """Markdown for the rule reference, rendered from the cross-field rules.

    The Markdown is written in ``templates/rule_reference.md.jinja``. This class gives
    the template the schema, the rules and the terms of the concepts they name.

    Args:
        schema: The field schema the rules relate the fields of.
        vocabularies: Where the vocabulary fields take their allowed values from.
            Without it, the cache directory.
        rules: The rules to render.
    """

    def __init__(
        self,
        schema: Schema,
        vocabularies: Vocabularies | None = None,
        rules: Sequence[Rule] = RULES,
    ) -> None:
        self.schema = schema
        self.vocabularies = Vocabularies() if vocabularies is None else vocabularies
        self.rules = tuple(rules)
        self.concepts = FieldConcepts.resolve(
            schema,
            [pair for rule in self.rules for pair in rule.concepts()],
            self.vocabularies,
        )
        self.environment = Environment(
            loader=FileSystemLoader(TEMPLATES),
            undefined=StrictUndefined,
            keep_trailing_newline=True,
        )
        self.environment.filters.update(
            cell=FieldReference.cell, code=FieldReference.code
        )
        self.macros: Any = self.environment.get_template(
            "rule_reference.md.jinja"
        ).make_module(
            {
                "schema": schema,
                "rules": self.rules,
                "domain_of": self.domain_of,
                "terms": self.terms,
                "concepts": self.concepts,
                "source": FieldReference.source,
                "problem": str(Kind.RULE),
            }
        )
        self.environment.globals.update(domains=self.domains, entries=self.entries)

    def terms(self, code: str) -> dict[URIRef, str]:
        """Map each allowed value of a field that has a concept to its term.

        Args:
            code: The field's code.

        Returns:
            The term of each allowed value that belongs to a vocabulary, by concept.
        """
        return FieldConcepts.terms_of(self.schema.get_field(code), self.vocabularies)

    def domain_of(self, concept: URIRef) -> Domain | None:
        """Find the domain an exploration method belongs to.

        Args:
            concept: The exploration method's concept.

        Returns:
            The domain, or None when no rule's domain holds the method.
        """
        methods = self.concepts[BOREHOLE.field]
        return next(
            (
                d
                for d in (BOREHOLE, PROBE_SENSING)
                if concept in methods.expand(d.concepts)
            ),
            None,
        )

    def domains(self) -> str:
        """Write the table that maps each exploration method to its domain.

        Returns:
            A Markdown table with a row per allowed value of the exploration method
            field, in the order the field lists them.
        """
        return str(self.macros.domains(BOREHOLE.field))

    def entries(self) -> str:
        """Write the entry of every rule, in the order of the rules.

        Returns:
            Markdown for the entries.
        """
        return str(self.macros.entries())

    def render(self, page: str) -> str:
        """Render a page whose source calls ``domains()`` or ``entries()``.

        Args:
            page: The raw source of a page.

        Returns:
            The page with each call replaced by the Markdown it stands for.
        """
        return self.environment.from_string(page).render()


@cache
def rule_reference() -> RuleReference:
    """Read the packaged field schema once for the whole build."""
    vocabularies = Vocabularies()
    return RuleReference(load_schema(vocabularies=vocabularies), vocabularies)


def source_read(app: Sphinx, docname: str, source: list[str]) -> None:
    """Render the rule reference page, which is a template."""
    if docname == PAGE:
        source[0] = rule_reference().render(source[0])


def setup(app: Sphinx) -> dict[str, Any]:
    """Register the extension's handler.

    Args:
        app: The Sphinx application.

    Returns:
        The extension's metadata.
    """
    app.connect("source-read", source_read)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
