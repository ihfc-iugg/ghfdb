from frictionless import Schema

import ghfdb.qc.concepts as concepts
from ghfdb.fields import Vocabularies, allowed_values

DEPTH = concepts.VOCABULARIES.count("/") + 2


class TestConcepts:
    def test_every_concept_is_a_concept_the_vocabularies_publish_now(
        self, schema: Schema, published_vocabularies: Vocabularies
    ) -> None:
        published = {
            value.uri
            for field in schema.fields
            for value in allowed_values(field, published_vocabularies)
        }
        named = {
            value
            for value in vars(concepts).values()
            if isinstance(value, str) and value.count("/") == DEPTH
        }

        assert named
        assert named - published == set()
