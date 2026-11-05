from collections.abc import Callable
from dataclasses import replace

import pandas
import pytest
from frictionless import Schema

from ghfdb.fields import MissingSchemeError, Vocabularies
from ghfdb.qc.check import DatasetCheck
from ghfdb.qc.rules import CF_1, CF_2, CF_3, RULES, Condition, Rule

Children = Callable[..., pandas.DataFrame]
CONDUCTIVITY_SOURCES = "https://w3id.org/ihfc-iugg/vocabularies/conductivity-sources"


class TestResolution:
    def test_every_concept_of_the_rules_resolves_to_a_term_of_its_field(
        self, schema: Schema, children: Children, published_vocabularies: Vocabularies
    ) -> None:
        check = DatasetCheck(children({}), schema, RULES, published_vocabularies)

        concepts = [concept for rule in RULES for concept in rule.concepts()]
        assert concepts
        for code, uri in concepts:
            assert check.terms[code, uri] in schema.get_field(code).constraints["enum"]

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
        assert CF_1.fields(schema) == ("P12", "C5", "C31", "C32")

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
        elsewhere = f"{CONDUCTIVITY_SOURCES}/core_samples"
        broken = replace(CF_3, when=Condition("C42", (elsewhere,)))

        with pytest.raises(MissingSchemeError) as error:
            DatasetCheck(children({}), schema, (broken,), published_vocabularies)

        assert "CF-3" in str(error.value)
        assert elsewhere in str(error.value)

    def test_a_concept_the_vocabulary_does_not_publish_names_the_rule(
        self, schema: Schema, children: Children, published_vocabularies: Vocabularies
    ) -> None:
        withdrawn = f"{CONDUCTIVITY_SOURCES}/withdrawn_concept"
        broken = replace(CF_3, then=Condition("C41", (withdrawn,)))

        with pytest.raises(MissingSchemeError) as error:
            DatasetCheck(children({}), schema, (broken,), published_vocabularies)

        assert "CF-3" in str(error.value)
        assert withdrawn in str(error.value)

    @pytest.mark.parametrize("rule", RULES, ids=lambda rule: rule.identifier)
    def test_a_rule_draws_a_diagram_naming_its_fields(
        self, schema: Schema, rule: Rule
    ) -> None:
        diagram = rule.diagram(schema)

        assert diagram.startswith("flowchart")
        for code in rule.fields(schema):
            assert code in diagram

    def test_a_concept_of_a_field_the_schema_lacks_names_the_rule(
        self, schema: Schema, children: Children, published_vocabularies: Vocabularies
    ) -> None:
        broken = replace(CF_3, when=Condition("C9999", (CONDUCTIVITY_SOURCES,)))

        with pytest.raises(MissingSchemeError, match="CF-3"):
            DatasetCheck(children({}), schema, (broken,), published_vocabularies)
