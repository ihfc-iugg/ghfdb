from collections.abc import Callable
from dataclasses import replace

import pandas
import pytest
from frictionless import Schema

from ghfdb.qc.check import DatasetCheck
from ghfdb.qc.rules import CF_1, CF_2, CF_3, RULES, Condition, Rule
from ghfdb.vocabularies import MissingSchemeError, Vocabularies

Children = Callable[..., pandas.DataFrame]


class TestResolution:
    def test_every_concept_of_the_rules_resolves_to_a_term_of_its_field(
        self, schema: Schema, children: Children, published_vocabularies: Vocabularies
    ) -> None:
        check = DatasetCheck(children({}), schema, RULES, published_vocabularies)

        concepts = [concept for rule in RULES for concept in rule.concepts()]
        assert concepts
        for code, name in concepts:
            assert check.terms[code, name] in schema.get_field(code).constraints["enum"]

    def test_the_rules_resolve_to_the_terms_the_vocabularies_publish_now(
        self, schema: Schema, children: Children, published_vocabularies: Vocabularies
    ) -> None:
        fresh = Vocabularies(published_vocabularies.session)

        check = DatasetCheck(children({}), schema, RULES, fresh)

        assert len(check.terms) == len(
            {concept for rule in RULES for concept in rule.concepts()}
        )

    def test_the_borehole_rule_relates_the_fields_mandatory_for_boreholes_only(
        self, schema: Schema
    ) -> None:
        assert CF_1.fields(schema) == ("P12", "C4", "C5", "C31", "C32")

    def test_the_probe_sensing_rule_relates_the_fields_mandatory_for_probing_only(
        self, schema: Schema
    ) -> None:
        assert CF_2.fields(schema) == ("P12", "C6", "C23")

    def test_the_conductivity_rule_relates_the_location_and_the_source(
        self, schema: Schema
    ) -> None:
        assert CF_3.fields(schema) == ("C42", "C41")

    def test_a_concept_that_is_not_an_allowed_value_of_its_field_names_the_rule(
        self, schema: Schema, children: Children, published_vocabularies: Vocabularies
    ) -> None:
        elsewhere = "core-samples"
        broken = replace(CF_3, when=Condition("C42", (elsewhere,)))

        with pytest.raises(MissingSchemeError) as error:
            DatasetCheck(children({}), schema, (broken,), published_vocabularies)

        assert "CF-3" in str(error.value)
        assert "C42" in str(error.value)
        assert elsewhere in str(error.value)

    def test_a_concept_the_vocabulary_does_not_publish_names_the_rule(
        self, schema: Schema, children: Children, published_vocabularies: Vocabularies
    ) -> None:
        withdrawn = "withdrawn_concept"
        broken = replace(CF_3, then=Condition("C41", (withdrawn,)))

        with pytest.raises(MissingSchemeError) as error:
            DatasetCheck(children({}), schema, (broken,), published_vocabularies)

        assert "CF-3" in str(error.value)
        assert "C41" in str(error.value)
        assert withdrawn in str(error.value)

    @pytest.mark.parametrize("rule", RULES, ids=lambda rule: rule.identifier)
    def test_a_rule_draws_a_diagram_naming_its_fields(
        self,
        schema: Schema,
        rule: Rule,
        children: Children,
        published_vocabularies: Vocabularies,
    ) -> None:
        terms = DatasetCheck(children({}), schema, RULES, published_vocabularies).terms

        diagram = rule.diagram(schema, terms)

        assert diagram.startswith("flowchart")
        for code in rule.fields(schema):
            assert code in diagram

    def test_a_rule_that_allows_values_draws_the_terms_it_names(
        self, schema: Schema, children: Children, published_vocabularies: Vocabularies
    ) -> None:
        terms = DatasetCheck(children({}), schema, RULES, published_vocabularies).terms

        diagram = CF_3.diagram(schema, terms)

        for condition in (CF_3.when, CF_3.then):
            for name in condition.concepts:
                assert terms[condition.field, name] in diagram

    def test_a_rule_that_allows_several_values_joins_their_terms_with_or(
        self, schema: Schema, children: Children, published_vocabularies: Vocabularies
    ) -> None:
        several = replace(
            CF_3, then=Condition("C41", ("assumed-from-literature", "core-samples"))
        )
        terms = DatasetCheck(
            children({}), schema, (several,), published_vocabularies
        ).terms

        diagram = several.diagram(schema, terms)

        literature = terms["C41", "assumed-from-literature"]
        assert f"{literature} or {terms['C41', 'core-samples']}" in diagram

    def test_the_rules_of_two_domains_draw_different_conditions(
        self, schema: Schema, children: Children, published_vocabularies: Vocabularies
    ) -> None:
        terms = DatasetCheck(children({}), schema, RULES, published_vocabularies).terms

        borehole = CF_1.diagram(schema, terms)
        probing = CF_2.diagram(schema, terms)

        assert CF_1.domain.description in borehole
        assert CF_2.domain.description in probing
        assert CF_1.domain.description not in probing
        assert CF_2.domain.description not in borehole

    def test_a_concept_of_a_field_the_schema_lacks_names_the_rule(
        self, schema: Schema, children: Children, published_vocabularies: Vocabularies
    ) -> None:
        broken = replace(CF_3, when=Condition("C9999", ("core-samples",)))

        with pytest.raises(MissingSchemeError, match="CF-3"):
            DatasetCheck(children({}), schema, (broken,), published_vocabularies)


DRILLING_TERM = ("P12", "drilling")
LITERATURE_TERM = ("C42", "literature")
ASSUMED_TERM = ("C41", "assumed-from-literature")


def with_separator(schema: Schema, *codes: str) -> Schema:
    """Copy a schema, making fields take several values in a cell."""
    descriptor = schema.to_descriptor()
    for described in descriptor["fields"]:
        if described["name"] in codes:
            described["separator"] = ";"
    return Schema.from_descriptor(descriptor)


class Terms:
    """Read the term of any concept of a field from the vocabularies."""

    def __init__(self, schema: Schema, vocabularies: Vocabularies) -> None:
        self.check = DatasetCheck(pandas.DataFrame(), schema)
        self.vocabularies = vocabularies

    def __call__(self, code: str, name: str) -> str:
        return self.check.names(code, self.vocabularies)[name]


@pytest.fixture
def term(schema: Schema, published_vocabularies: Vocabularies) -> Terms:
    return Terms(schema, published_vocabularies)


class TestRuleProblems:
    @pytest.fixture(autouse=True)
    def checking(self, schema: Schema, published_vocabularies: Vocabularies) -> None:
        self.schema = schema
        self.vocabularies = published_vocabularies

    def lines(
        self, frame: pandas.DataFrame, schema: Schema | None = None
    ) -> list[tuple[int, str, str, str | None]]:
        """Find the rule lines as (row, code, rule, related)."""
        check = DatasetCheck(frame, schema or self.schema, RULES, self.vocabularies)
        problems = check.problems()
        found = problems[problems["kind"] == "rule"]
        return [
            (
                line["row"],
                line["code"],
                line["rule"],
                None if pandas.isna(line["related"]) else line["related"],
            )
            for line in found.to_dict("records")
        ]

    def test_an_empty_field_required_for_the_domain_is_one_line_with_its_condition(
        self, children: Children, term: Terms
    ) -> None:
        frame = children({"P12": term(*DRILLING_TERM), "C5": None})

        assert self.lines(frame) == [
            (9, "C5", "CF-1", f"P12 explo_method {term(*DRILLING_TERM)}")
        ]

    def test_a_field_of_spaces_only_is_empty(
        self, children: Children, term: Terms
    ) -> None:
        frame = children({"P12": term(*DRILLING_TERM), "C5": "  "})

        assert [line[1] for line in self.lines(frame)] == ["C5"]

    def test_the_line_carries_the_empty_value_and_the_column_name_to_fill(
        self, children: Children, term: Terms
    ) -> None:
        frame = children({"P12": term(*DRILLING_TERM), "C5": "  "})

        problems = DatasetCheck(frame, self.schema, RULES, self.vocabularies).problems()

        (line,) = problems[problems["kind"] == "rule"].to_dict("records")
        assert line["column_name"] == "q_bottom"
        assert line["value"] == "  "
        assert pandas.isna(line["suggestion"])

    def test_every_empty_required_field_is_a_line(
        self, children: Children, term: Terms
    ) -> None:
        frame = children({"P12": term(*DRILLING_TERM), "C5": None, "C32": None})

        assert [line[1] for line in self.lines(frame)] == ["C5", "C32"]

    def test_the_probe_sensing_rule_requires_its_own_fields(
        self, children: Children, term: Terms
    ) -> None:
        probing = term("P12", "probing-onshore")
        frame = children({"P12": probing, "C6": None, "C23": None, "C5": None})

        assert self.lines(frame) == [
            (9, "C6", "CF-2", f"P12 explo_method {probing}"),
            (9, "C23", "CF-2", f"P12 explo_method {probing}"),
        ]

    @pytest.mark.parametrize("method", [None, "no such method"])
    def test_an_empty_or_unknown_exploration_method_requires_nothing(
        self, children: Children, method: str | None
    ) -> None:
        frame = children({"P12": method, "C5": None, "C6": None})

        assert self.lines(frame) == []

    def test_an_exploration_method_in_neither_domain_requires_nothing(
        self, children: Children, term: Terms
    ) -> None:
        frame = children({"P12": term("P12", "other"), "C5": None, "C6": None})

        assert self.lines(frame) == []

    def test_several_exploration_methods_in_a_cell_are_all_read(
        self, children: Children, term: Terms
    ) -> None:
        both = f"{term(*DRILLING_TERM)}; {term('P12', 'probing-onshore')}"
        frame = children(
            {"P12": both, "C5": None, "C6": None},
            {"P12": f"{both}; no such method", "C5": None, "C6": None},
        )

        found = self.lines(frame, with_separator(self.schema, "P12"))

        assert [(row, code) for row, code, *_ in found] == [(9, "C5"), (9, "C6")]

    def test_a_disallowed_value_is_a_line_naming_the_value_and_its_condition(
        self, children: Children, term: Terms
    ) -> None:
        frame = children(
            {"C42": term(*LITERATURE_TERM), "C41": term("C41", "core-samples")}
        )

        assert self.lines(frame) == [
            (9, "C41", "CF-3", f"C42 tc_location {term(*LITERATURE_TERM)}")
        ]
        problems = DatasetCheck(frame, self.schema, RULES, self.vocabularies).problems()
        assert list(problems["value"]) == [term("C41", "core-samples")]

    def test_the_allowed_value_is_no_line(
        self, children: Children, term: Terms
    ) -> None:
        frame = children(
            {"C42": term(*LITERATURE_TERM), "C41": term(*ASSUMED_TERM)},
            {"C42": term("C42", "actual"), "C41": term("C41", "core-samples")},
            {"C42": None, "C41": term("C41", "core-samples")},
            {"C42": "no such location", "C41": term("C41", "core-samples")},
        )

        assert self.lines(frame) == []

    def test_a_disallowed_value_not_in_the_vocabulary_is_skipped(
        self, children: Children, term: Terms
    ) -> None:
        frame = children({"C42": term(*LITERATURE_TERM), "C41": "no such source"})

        assert self.lines(frame) == []

    def test_each_disallowed_value_in_a_cell_is_a_line(
        self, children: Children, term: Terms
    ) -> None:
        core, cutting = term("C41", "core-samples"), term("C41", "cutting-samples")
        frame = children(
            {
                "C42": term(*LITERATURE_TERM),
                "C41": f"{core}; {term(*ASSUMED_TERM)}; {cutting}",
            }
        )

        problems = DatasetCheck(
            frame, with_separator(self.schema, "C41"), RULES, self.vocabularies
        ).problems()

        found = problems[problems["kind"] == "rule"]
        assert list(found["value"]) == [core, cutting]

    def test_a_value_not_in_the_vocabulary_in_the_limited_cell_gives_no_rule_line(
        self, children: Children, term: Terms
    ) -> None:
        core = term("C41", "core-samples")
        frame = children({"C42": term(*LITERATURE_TERM), "C41": f"{core}; nonsense"})

        problems = DatasetCheck(
            frame, with_separator(self.schema, "C41"), RULES, self.vocabularies
        ).problems()

        assert list(problems["kind"]) == ["not in vocabulary"]
        assert list(problems["value"]) == ["nonsense"]

    def test_several_values_in_the_condition_cell_hold_when_all_are_published(
        self, children: Children, term: Terms
    ) -> None:
        both = f"{term(*LITERATURE_TERM)}; {term('C42', 'actual')}"
        frame = children(
            {"C42": both, "C41": term("C41", "core-samples")},
            {"C42": f"{both}; nonsense", "C41": term("C41", "core-samples")},
        )

        found = self.lines(frame, with_separator(self.schema, "C42"))

        assert [(row, code) for row, code, *_ in found] == [(9, "C41")]

    @pytest.mark.parametrize("method", ["C31", "C32"])
    def test_an_egrt_temperature_method_requires_the_probe_pulse_conductivity_method(
        self, children: Children, term: Terms, method: str
    ) -> None:
        egrt = term(method, "EGRT")
        other = term("C43", "pointSource")
        frame = children({method: egrt, "C43": other})

        problems = DatasetCheck(frame, self.schema, RULES, self.vocabularies).problems()

        found = problems[problems["kind"] == "rule"]
        column = self.schema.get_field(method).custom["columnName"]
        assert list(found["code"]) == ["C43"]
        assert list(found["rule"]) == ["CF-4"]
        assert list(found["value"]) == [other]
        assert list(found["related"]) == [f"{method} {column} {egrt}"]

    @pytest.mark.parametrize(
        ("top", "bottom", "conductivity"),
        [
            ("EGRT", "EGRT", "probePulse"),
            ("EGRT", None, "probePulse"),
            (None, "EGRT", "probePulse"),
            ("other", "other", "pointSource"),
            (None, None, "pointSource"),
        ],
        ids=["both", "top", "bottom", "neither", "empty"],
    )
    def test_the_probe_pulse_conductivity_method_or_no_egrt_breaks_nothing(
        self,
        children: Children,
        term: Terms,
        top: str | None,
        bottom: str | None,
        conductivity: str,
    ) -> None:
        frame = children(
            {
                "C31": None if top is None else term("C31", top),
                "C32": None if bottom is None else term("C32", bottom),
                "C43": term("C43", conductivity),
            }
        )

        assert [line for line in self.lines(frame) if line[2] == "CF-4"] == []

    def test_an_egrt_at_the_bottom_names_the_bottom_when_the_top_has_another_method(
        self, children: Children, term: Terms
    ) -> None:
        other_top = term("C31", "other")
        egrt = term("C32", "EGRT")
        frame = children(
            {"C31": other_top, "C32": egrt, "C43": term("C43", "pointSource")}
        )

        found = [line for line in self.lines(frame) if line[2] == "CF-4"]

        assert found == [(9, "C43", "CF-4", f"C32 T_method_bottom {egrt}")]

    @pytest.mark.parametrize("missing", ["P12", "C5", "C6", "C41", "C42"])
    def test_a_rule_whose_field_has_no_column_gives_no_line(
        self, children: Children, term: Terms, missing: str
    ) -> None:
        frame = children(
            {"P12": term(*DRILLING_TERM), "C5": None},
            {"P12": term("P12", "probing-onshore"), "C6": None},
            {"C42": term(*LITERATURE_TERM), "C41": term("C41", "core-samples")},
        ).drop(columns=missing)

        codes = {code for _, code, *_ in self.lines(frame)}

        assert missing not in codes
        assert codes <= {"C5", "C6", "C23", "C31", "C32", "C41"}

    def test_a_child_breaking_two_rules_has_its_rule_lines_after_its_field_lines(
        self, children: Children, term: Terms
    ) -> None:
        frame = children(
            {
                "P12": term(*DRILLING_TERM),
                "C5": None,
                "C31": None,
                "C42": term(*LITERATURE_TERM),
                "C41": term("C41", "core-samples"),
                "C1": "abc",
            },
            {"C1": "abc"},
        )

        problems = DatasetCheck(frame, self.schema, RULES, self.vocabularies).problems()

        assert [
            (p["row"], p["code"], p["kind"]) for p in problems.to_dict("records")
        ] == [
            (9, "C1", "wrong type"),
            (9, "C5", "rule"),
            (9, "C31", "rule"),
            (9, "C41", "rule"),
            (10, "C1", "wrong type"),
        ]

    def test_only_a_rule_line_carries_a_rule_and_a_related_field(
        self, children: Children, term: Terms
    ) -> None:
        frame = children({"P12": term(*DRILLING_TERM), "C5": None, "C1": "abc"})

        problems = DatasetCheck(frame, self.schema, RULES, self.vocabularies).problems()

        filled = {
            kind: (not pandas.isna(line["rule"]), not pandas.isna(line["related"]))
            for kind, line in zip(
                problems["kind"], problems.to_dict("records"), strict=True
            )
        }
        assert filled == {"rule": (True, True), "wrong type": (False, False)}


class TestWorkedExamples:
    @pytest.fixture(autouse=True)
    def checking(self, schema: Schema, published_vocabularies: Vocabularies) -> None:
        self.schema = schema
        self.vocabularies = published_vocabularies

    def test_a_valid_child_breaks_no_rule(self, children: Children) -> None:
        problems = DatasetCheck(
            children({}), self.schema, RULES, self.vocabularies
        ).problems()

        assert problems.empty

    @pytest.mark.parametrize("rule", RULES, ids=lambda rule: rule.identifier)
    def test_an_example_gives_exactly_its_expected_rule_problem(
        self, children: Children, term: Terms, rule: Rule
    ) -> None:
        changes = {
            code: term(code, value) if code in dict(rule.example.concepts()) else value
            for code, value in rule.example.values.items()
        }
        condition = rule.fields(self.schema)[0]
        field = self.schema.get_field(condition)

        problems = DatasetCheck(
            children(changes), self.schema, RULES, self.vocabularies
        ).problems()

        assert [
            (line["row"], line["code"], line["kind"], line["rule"], line["related"])
            for line in problems.to_dict("records")
        ] == [
            (
                9,
                code,
                "rule",
                rule.identifier,
                f"{condition} {field.custom['columnName']} {changes[condition]}",
            )
            for code in rule.example.expected
        ]
