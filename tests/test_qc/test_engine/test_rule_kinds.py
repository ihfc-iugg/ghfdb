from collections.abc import Callable
from dataclasses import replace

import pandas
import pytest
from frictionless import Schema

from ghfdb.qc.check import DatasetCheck
from ghfdb.qc.engine.rule_kinds import Condition, Rule
from ghfdb.qc.rules import CF_1, CF_2, CF_3, RULES
from ghfdb.vocabularies import Vocabularies, concepts

Children = Callable[..., pandas.DataFrame]
SOURCE = concepts.tc_source


class TestDiagram:
    @pytest.mark.parametrize("rule", RULES, ids=lambda rule: rule.identifier)
    def test_a_rule_draws_a_diagram_naming_its_fields(
        self,
        schema: Schema,
        rule: Rule,
        children: Children,
        published_vocabularies: Vocabularies,
    ) -> None:
        resolved = DatasetCheck(
            children({}), schema, RULES, published_vocabularies
        ).concepts

        diagram = rule.diagram(schema, resolved)

        assert diagram.startswith("flowchart")
        for code in rule.fields(schema):
            assert code in diagram

    def test_a_rule_that_allows_values_draws_the_terms_it_names(
        self, schema: Schema, children: Children, published_vocabularies: Vocabularies
    ) -> None:
        resolved = DatasetCheck(
            children({}), schema, RULES, published_vocabularies
        ).concepts

        diagram = CF_3.diagram(schema, resolved)

        for condition in (CF_3.when, CF_3.then):
            for term in resolved[condition.field].terms_for(condition.concepts):
                assert term in diagram

    def test_a_rule_that_allows_several_values_joins_their_terms_with_or(
        self, schema: Schema, children: Children, published_vocabularies: Vocabularies
    ) -> None:
        several = replace(
            CF_3,
            then=Condition(
                "C41", (SOURCE["assumed-from-literature"], SOURCE["core-samples"])
            ),
        )
        resolved = DatasetCheck(
            children({}), schema, (several,), published_vocabularies
        ).concepts

        diagram = several.diagram(schema, resolved)

        terms = resolved["C41"].terms
        literature = terms[SOURCE["assumed-from-literature"]]
        assert f"{literature} or {terms[SOURCE['core-samples']]}" in diagram

    def test_the_rules_of_two_domains_draw_different_conditions(
        self, schema: Schema, children: Children, published_vocabularies: Vocabularies
    ) -> None:
        resolved = DatasetCheck(
            children({}), schema, RULES, published_vocabularies
        ).concepts

        borehole = CF_1.diagram(schema, resolved)
        probing = CF_2.diagram(schema, resolved)

        assert CF_1.domain.description in borehole
        assert CF_2.domain.description in probing
        assert CF_1.domain.description not in probing
        assert CF_2.domain.description not in borehole
