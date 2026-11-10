import re
from collections.abc import Mapping
from typing import Any

import pytest
from conftest import worked_document
from frictionless import Schema

from ghfdb.fields import MissingSchemeError, Vocabularies, allowed_values
from ghfdb.qc import borehole, probe
from ghfdb.qc.concepts import DRILLING, PRESENT_CORRECTED
from ghfdb.qc.criteria import CRITERIA, term_uris
from ghfdb.qc.rules import EXPLORATION_METHOD
from ghfdb.qc.scores import Scores


@pytest.fixture(scope="module")
def worked_criteria() -> Mapping[str, str]:
    criteria: Mapping[str, str] = worked_document()["criteria"]
    return criteria


class Withdrawing(Vocabularies):
    """Vocabularies in which one concept is no longer an allowed value."""

    def __init__(self, vocabularies: Vocabularies, uri: str) -> None:
        self.vocabularies = vocabularies
        self.uri = uri

    def allowed_values(self, vocabulary: Mapping[str, str | None]) -> Any:
        values = self.vocabularies.allowed_values(vocabulary)
        return tuple(value for value in values if value.uri != self.uri)


class TestCriteria:
    def test_every_criterion_has_the_identifier_the_worked_examples_use(
        self, worked_criteria: Mapping[str, str]
    ) -> None:
        assert set(CRITERIA) <= set(worked_criteria)
        assert all(key == criterion.identifier for key, criterion in CRITERIA.items())

    def test_every_criterion_is_declared_once(self) -> None:
        declared = [
            *probe.T_CRITERIA,
            *probe.TC_CRITERIA,
            *borehole.T_CRITERIA,
            *borehole.TC_CRITERIA,
        ]

        assert len(CRITERIA) == len(declared)

    def test_every_criterion_has_a_source_a_title_and_something_to_read(self) -> None:
        for criterion in CRITERIA.values():
            assert criterion.source, criterion.identifier
            assert criterion.title, criterion.identifier
            assert criterion.table.reads(), criterion.identifier
            assert criterion.table.rows(), criterion.identifier


class TestTermUris:
    def test_every_concept_the_scheme_names_resolves_to_the_term_its_field_accepts(
        self, schema: Schema, published_vocabularies: Vocabularies
    ) -> None:
        concepts = Scores.concepts()

        uris = term_uris(schema, concepts, published_vocabularies)

        for code, uri in concepts:
            field = schema.get_field(code)
            accepted = {
                v.uri: v.term for v in allowed_values(field, published_vocabularies)
            }
            assert uris[code][accepted[uri]] == uri, (code, uri)

    def test_a_term_the_scheme_does_not_name_still_has_its_concept(
        self, schema: Schema, published_vocabularies: Vocabularies
    ) -> None:
        field = schema.get_field("C31")
        unnamed = next(
            v
            for v in allowed_values(field, published_vocabularies)
            if v.uri and (field.name, v.uri) not in Scores.concepts()
        )

        uris = term_uris(schema, Scores.concepts(), published_vocabularies)

        assert uris["C31"][unnamed.term] == unnamed.uri

    def test_the_fields_resolved_are_those_the_scheme_names(
        self, schema: Schema, published_vocabularies: Vocabularies
    ) -> None:
        uris = term_uris(schema, Scores.concepts(), published_vocabularies)

        assert set(uris) == {code for code, _ in Scores.concepts()}

    def test_a_concept_the_vocabulary_no_longer_has_fails_naming_field_and_concept(
        self, schema: Schema, published_vocabularies: Vocabularies
    ) -> None:
        withdrawn = Withdrawing(published_vocabularies, DRILLING)

        with pytest.raises(MissingSchemeError) as raised:
            term_uris(schema, Scores.concepts(), withdrawn)

        assert re.search(
            rf"{EXPLORATION_METHOD}.*{re.escape(DRILLING)}", str(raised.value)
        )

    def test_a_concept_the_field_does_not_allow_fails_naming_it(
        self, schema: Schema, published_vocabularies: Vocabularies
    ) -> None:
        wrong = (*Scores.concepts(), (EXPLORATION_METHOD, PRESENT_CORRECTED))

        with pytest.raises(MissingSchemeError, match=re.escape(PRESENT_CORRECTED)):
            term_uris(schema, wrong, published_vocabularies)

    def test_a_concept_of_a_field_outside_the_schema_fails_naming_it(
        self, schema: Schema, published_vocabularies: Vocabularies
    ) -> None:
        unknown = (*Scores.concepts(), ("Z99", DRILLING))

        with pytest.raises(MissingSchemeError, match="Z99"):
            term_uris(schema, unknown, published_vocabularies)
