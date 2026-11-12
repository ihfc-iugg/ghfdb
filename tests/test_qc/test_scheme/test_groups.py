import pytest
from frictionless import Schema
from rdflib import URIRef

from ghfdb.fields.schema import FieldConcepts
from ghfdb.qc.scheme.groups import (
    AMBIENT_OR_UNSPECIFIED,
    DRY_UNSPECIFIED_OR_OTHER,
    FULL_IN_SITU,
    PARTIAL_IN_SITU,
)
from ghfdb.vocabularies import Vocabularies

PRESSURE_AND_TEMPERATURE = "C45"
SATURATION = "C44"


class TestGroups:
    @pytest.mark.parametrize(
        ("code", "group"),
        [
            (SATURATION, DRY_UNSPECIFIED_OR_OTHER),
            (PRESSURE_AND_TEMPERATURE, FULL_IN_SITU),
            (PRESSURE_AND_TEMPERATURE, PARTIAL_IN_SITU),
            (PRESSURE_AND_TEMPERATURE, AMBIENT_OR_UNSPECIFIED),
        ],
        ids=["dry", "full", "partial", "ambient"],
    )
    def test_every_concept_of_a_group_is_an_allowed_value_of_its_field(
        self,
        schema: Schema,
        published_vocabularies: Vocabularies,
        code: str,
        group: tuple[URIRef, ...],
    ) -> None:
        resolved = FieldConcepts.resolve(
            schema, [(code, concept) for concept in group], published_vocabularies
        )

        assert set(group) <= set(resolved[code].terms)

    def test_the_groups_of_pressure_and_temperature_conditions_share_no_concept(
        self,
    ) -> None:
        groups = [FULL_IN_SITU, PARTIAL_IN_SITU, AMBIENT_OR_UNSPECIFIED]

        concepts = [concept for group in groups for concept in group]

        assert len(concepts) == len(set(concepts))
