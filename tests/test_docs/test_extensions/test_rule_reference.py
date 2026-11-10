import re
from dataclasses import replace

import pytest
from extensions.field_reference import FieldReference
from extensions.rule_reference import RuleReference
from frictionless import Schema

from ghfdb.fields import Vocabularies, allowed_values
from ghfdb.qc.rules import BOREHOLE, PROBE_SENSING, RULES, Rule

MISSING = "—"
RELATED_FIELDS = {
    "CF-1": ("P12", "C4", "C5", "C31", "C32"),
    "CF-2": ("P12", "C6", "C23"),
    "CF-3": ("C42", "C41"),
}


@pytest.fixture(scope="module")
def reference(schema: Schema, published_vocabularies: Vocabularies) -> RuleReference:
    return RuleReference(schema, published_vocabularies)


@pytest.fixture(scope="module")
def field_reference(
    schema: Schema, published_vocabularies: Vocabularies
) -> FieldReference:
    return FieldReference(schema, published_vocabularies)


def section_of(markdown: str, rule: Rule) -> str:
    """Return the text of one rule's entry."""
    marker = f"({rule.identifier.lower()})=\n"
    start = markdown.index(marker)
    following = markdown.find("\n\n(", start + len(marker))
    return markdown[start:] if following == -1 else markdown[start:following]


def rows_of(section: str) -> list[list[str]]:
    """Return the cells of each body row of the tables in a section."""
    rows = [
        [cell.strip() for cell in line.strip().strip("|").split(" | ")]
        for line in section.splitlines()
        if line.startswith("|")
    ]
    return [row for row in rows if not set("".join(row)) <= set("-|: ")][1:]


def terms_of(
    schema: Schema, vocabularies: Vocabularies, code: str
) -> dict[str | None, str]:
    """Map the concept URI of each allowed value of a field to its term."""
    field = schema.get_field(code)
    return {value.uri: value.term for value in allowed_values(field, vocabularies)}


class TestRuleEntries:
    def test_the_rules_are_the_three_declared_ones(self) -> None:
        assert {rule.identifier for rule in RULES} == {"CF-1", "CF-2", "CF-3"}

    def test_each_rule_has_one_entry_anchored_by_its_lowercased_identifier(
        self, reference: RuleReference
    ) -> None:
        markdown = reference.entries()

        anchors = re.findall(r"^\(([^)]+)\)=$", markdown, re.MULTILINE)
        assert anchors == ["cf-1", "cf-2", "cf-3"]

    def test_the_heading_sits_one_level_below_the_page_title(
        self, reference: RuleReference
    ) -> None:
        for rule in RULES:
            section = section_of(reference.entries(), rule)

            headings = re.findall(r"^(#+) (.*)$", section, re.MULTILINE)
            assert [level for level, _ in headings] == ["##"], rule.identifier
            assert rule.identifier in headings[0][1]

    def test_every_entry_has_its_statement_reasoning_and_source(
        self, schema: Schema, reference: RuleReference, field_reference: FieldReference
    ) -> None:
        for rule in RULES:
            section = section_of(reference.entries(), rule)

            assert rule.statement in section, rule.identifier
            assert rule.reasoning in section, rule.identifier
            assert field_reference.source(rule.source) in section, rule.identifier

    def test_every_entry_links_each_field_it_relates_to_its_field_entry(
        self, schema: Schema, reference: RuleReference
    ) -> None:
        for rule in RULES:
            section = section_of(reference.entries(), rule)

            for code in RELATED_FIELDS[rule.identifier]:
                assert f"{{ref}}`{code} <field-{code.lower()}>`" in section, (
                    rule.identifier,
                    code,
                )

    def test_every_entry_draws_the_rules_diagram_in_a_mermaid_block(
        self, schema: Schema, reference: RuleReference
    ) -> None:
        for rule in RULES:
            section = section_of(reference.entries(), rule)

            assert (
                "```{mermaid}\n"
                + rule.diagram(schema, reference.concept_terms)
                + "\n```"
                in section
            )

    def test_every_entry_has_an_example_table_with_a_row_per_field(
        self, schema: Schema, reference: RuleReference
    ) -> None:
        for rule in RULES:
            section = section_of(reference.entries(), rule)

            rows = rows_of(section)
            assert len(rows) == len(rule.example.values), rule.identifier
            for row, code in zip(rows, rule.example.values, strict=True):
                assert row[0] == f"{{ref}}`{code} <field-{code.lower()}>`"

    def test_the_example_shows_the_term_of_each_concept_and_a_dash_for_an_empty_cell(
        self,
        schema: Schema,
        published_vocabularies: Vocabularies,
        reference: RuleReference,
    ) -> None:
        for rule in RULES:
            rows = rows_of(section_of(reference.entries(), rule))

            for row, (code, value) in zip(
                rows, rule.example.values.items(), strict=True
            ):
                if value is None:
                    assert row[1] == MISSING, (rule.identifier, code)
                else:
                    term = terms_of(schema, published_vocabularies, code)[value]
                    assert row[1] == f"`{term}`", (rule.identifier, code)

    def test_the_example_marks_the_fields_the_check_reports_and_no_others(
        self, reference: RuleReference
    ) -> None:
        for rule in RULES:
            rows = rows_of(section_of(reference.entries(), rule))

            for row, code in zip(rows, rule.example.values, strict=True):
                reported = code in rule.example.expected
                assert (row[2] != MISSING) is reported, (rule.identifier, code)


class TestDomainTable:
    def test_every_exploration_method_is_listed_once_with_its_term(
        self,
        schema: Schema,
        published_vocabularies: Vocabularies,
        reference: RuleReference,
    ) -> None:
        rows = rows_of(reference.domains())

        terms = terms_of(schema, published_vocabularies, BOREHOLE.field)
        assert [row[0] for row in rows] == [f"`{term}`" for term in terms.values()]

    def test_methods_are_grouped_by_the_domains_of_the_rules(
        self,
        schema: Schema,
        published_vocabularies: Vocabularies,
        reference: RuleReference,
    ) -> None:
        rows = rows_of(reference.domains())
        terms = terms_of(schema, published_vocabularies, BOREHOLE.field)

        grouped: dict[str, set[str]] = {}
        for method, domain in rows:
            grouped.setdefault(domain, set()).add(method)
        borehole = {f"`{terms[uri]}`" for uri in BOREHOLE.concepts}
        probing = {f"`{terms[uri]}`" for uri in PROBE_SENSING.concepts}
        assert len(borehole) == 5
        assert len(probing) == 3
        assert sorted(map(frozenset, grouped.values()), key=len) == sorted(
            [
                frozenset(borehole),
                frozenset(probing),
                frozenset({f"`{t}`" for t in terms.values()} - borehole - probing),
            ],
            key=len,
        )
        assert len(grouped) == 3


class TestRender:
    def test_the_calls_in_a_page_are_replaced_by_the_markdown_they_stand_for(
        self, reference: RuleReference
    ) -> None:
        text = "# Rules\n\n{{ domains() }}\n\n{{ entries() }}\nafter\n"

        result = reference.render(text)

        assert "domains()" not in result and "entries()" not in result
        assert reference.domains() in result
        assert reference.entries() in result
        assert result.endswith("\nafter\n")

    def test_an_unknown_source_stops_the_build(
        self, schema: Schema, published_vocabularies: Vocabularies
    ) -> None:
        rule = replace(RULES[0], source="not-a-source")

        with pytest.raises(ValueError, match="Unknown source"):
            RuleReference(schema, published_vocabularies, (rule,)).entries()


class TestFieldReferenceRules:
    def test_a_field_lists_the_rules_that_relate_it_linked_to_their_entries(
        self, schema: Schema, field_reference: FieldReference
    ) -> None:
        for field in schema.fields:
            expected = [
                rule for rule, codes in RELATED_FIELDS.items() if field.name in codes
            ]
            section = field_reference.entries(field.custom["group"])
            entry = section[section.index(f"(field-{field.name.lower()})=\n") :]
            entry = entry.split("\n\n(field-", 1)[0]

            rows = [line for line in entry.splitlines() if line.startswith("| Rules ")]
            if not expected:
                assert rows == [], field.name
                continue
            assert len(rows) == 1, field.name
            found = re.findall(r"\{ref\}`([A-Z]+-\d+) <([a-z]+-\d+)>`", rows[0])
            assert found == [(name, name.lower()) for name in expected], field.name
