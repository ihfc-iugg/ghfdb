import re
from collections.abc import Mapping
from typing import Any

import pytest
from conftest import worked_document
from frictionless import Schema
from rdflib import Graph, URIRef

from ghfdb.fields import allowed_values
from ghfdb.fields.schema import FieldConcepts
from ghfdb.qc.borehole import BoreholeAndMine
from ghfdb.qc.criteria import CRITERIA
from ghfdb.qc.probe import ProbeSensing
from ghfdb.qc.rules import EXPLORATION_METHOD
from ghfdb.qc.scores import Scores
from ghfdb.vocabularies import MissingSchemeError, Vocabularies, concepts, local_name


@pytest.fixture(scope="module")
def worked_criteria() -> Mapping[str, str]:
    criteria: Mapping[str, str] = worked_document()["criteria"]
    return criteria


class Withdrawing(Vocabularies):
    """Vocabularies in which one concept is no longer an allowed value."""

    def __init__(self, vocabularies: Vocabularies, name: str) -> None:
        self.vocabularies = vocabularies
        self.name = name

    def allowed_values(self, vocabulary: Mapping[str, str | None]) -> Any:
        values = self.vocabularies.allowed_values(vocabulary)
        return tuple(
            value
            for value in values
            if value.uri and local_name(value.uri) != self.name
        )

    def graph(
        self,
        scheme: str,
        download: str | None = None,
        media_type: str | None = None,
    ) -> Graph:
        return self.vocabularies.graph(scheme, download, media_type)


class TestCriteria:
    def test_every_criterion_has_the_identifier_the_worked_examples_use(
        self, worked_criteria: Mapping[str, str]
    ) -> None:
        assert set(CRITERIA) <= set(worked_criteria)
        assert all(key == criterion.identifier for key, criterion in CRITERIA.items())

    def test_every_criterion_is_declared_once(self) -> None:
        declared = [*ProbeSensing.declared(), *BoreholeAndMine.declared()]

        assert len(CRITERIA) == len(declared)

    def test_every_criterion_has_a_source_a_title_and_something_to_read(self) -> None:
        for criterion in CRITERIA.values():
            assert criterion.source, criterion.identifier
            assert criterion.title, criterion.identifier
            assert criterion.table.reads(), criterion.identifier
            assert criterion.table.largest() < 0, criterion.identifier


class TestSchemeConcepts:
    def test_every_concept_the_scheme_names_resolves_to_the_term_its_field_accepts(
        self, schema: Schema, published_vocabularies: Vocabularies
    ) -> None:
        named = Scores.concepts()

        resolved = FieldConcepts.resolve(schema, named, published_vocabularies)

        for code, concept in named:
            accepted = {
                URIRef(v.uri): v.term
                for v in allowed_values(schema.get_field(code), published_vocabularies)
                if v.uri
            }
            assert resolved[code].terms == accepted, (code, concept)
            assert concept in accepted or concept in resolved[code].collections

    def test_a_term_the_scheme_does_not_name_still_has_its_concept(
        self, schema: Schema, published_vocabularies: Vocabularies
    ) -> None:
        field = schema.get_field("C31")
        named = {concept for code, concept in Scores.concepts() if code == field.name}
        unnamed = next(
            v
            for v in allowed_values(field, published_vocabularies)
            if v.uri and URIRef(v.uri) not in named
        )

        resolved = FieldConcepts.resolve(
            schema, Scores.concepts(), published_vocabularies
        )

        assert unnamed.uri
        assert resolved["C31"].concepts[unnamed.term] == URIRef(unnamed.uri)

    def test_the_fields_resolved_are_those_the_scheme_names(
        self, schema: Schema, published_vocabularies: Vocabularies
    ) -> None:
        resolved = FieldConcepts.resolve(
            schema, Scores.concepts(), published_vocabularies
        )

        assert set(resolved) == {code for code, _ in Scores.concepts()}

    def test_a_concept_the_vocabulary_no_longer_has_fails_naming_field_and_concept(
        self, schema: Schema, published_vocabularies: Vocabularies
    ) -> None:
        withdrawn = Withdrawing(published_vocabularies, "drilling")

        with pytest.raises(MissingSchemeError) as raised:
            FieldConcepts.resolve(schema, Scores.concepts(), withdrawn)

        assert re.search(rf"{EXPLORATION_METHOD}.*drilling", str(raised.value))

    def test_a_concept_the_field_does_not_allow_fails_naming_it(
        self, schema: Schema, published_vocabularies: Vocabularies
    ) -> None:
        wrong = (
            *Scores.concepts(),
            (EXPLORATION_METHOD, concepts.corr_S_flag["present-corrected"]),
        )

        with pytest.raises(
            MissingSchemeError, match=f"{EXPLORATION_METHOD}.*present-corrected"
        ):
            FieldConcepts.resolve(schema, wrong, published_vocabularies)

    def test_a_misspelt_concept_fails_naming_field_and_concept(
        self, schema: Schema, published_vocabularies: Vocabularies
    ) -> None:
        misspelt = (
            *Scores.concepts(),
            (EXPLORATION_METHOD, concepts.explo_method.drillling),
        )

        with pytest.raises(
            MissingSchemeError, match=f"{EXPLORATION_METHOD}.*drillling"
        ):
            FieldConcepts.resolve(schema, misspelt, published_vocabularies)

    def test_a_concept_of_a_field_outside_the_schema_fails_naming_it(
        self, schema: Schema, published_vocabularies: Vocabularies
    ) -> None:
        unknown = (*Scores.concepts(), ("Z99", concepts.explo_method.drilling))

        with pytest.raises(MissingSchemeError, match="Z99"):
            FieldConcepts.resolve(schema, unknown, published_vocabularies)
