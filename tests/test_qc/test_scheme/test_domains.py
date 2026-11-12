from frictionless import Schema

from ghfdb.fields.schema import FieldConcepts
from ghfdb.qc.scheme.domains import BOREHOLE, EXPLORATION_METHOD, PROBE_SENSING
from ghfdb.vocabularies import Vocabularies, concepts

METHOD = concepts.explo_method


class TestDomains:
    def methods(
        self, schema: Schema, published_vocabularies: Vocabularies
    ) -> FieldConcepts:
        resolved = FieldConcepts.resolve(
            schema,
            [
                (EXPLORATION_METHOD, concept)
                for domain in (BOREHOLE, PROBE_SENSING)
                for concept in domain.concepts
            ],
            published_vocabularies,
        )
        return resolved[EXPLORATION_METHOD]

    def test_the_borehole_domain_holds_the_methods_that_reach_the_rock_or_estimate(
        self, schema: Schema, published_vocabularies: Vocabularies
    ) -> None:
        methods = self.methods(schema, published_vocabularies)

        assert set(methods.expand(BOREHOLE.concepts)) == {
            METHOD.drilling,
            METHOD["drilling-clustering"],
            METHOD.mining,
            METHOD.tunneling,
            METHOD.indirect,
        }

    def test_the_probe_sensing_domain_holds_the_probing_methods(
        self, schema: Schema, published_vocabularies: Vocabularies
    ) -> None:
        methods = self.methods(schema, published_vocabularies)

        assert set(methods.expand(PROBE_SENSING.concepts)) == {
            METHOD["probing-onshore"],
            METHOD["probing-offshore"],
            METHOD["probing-clustering"],
        }

    def test_a_domain_is_named_by_the_collection_the_vocabulary_publishes(self) -> None:
        assert BOREHOLE.concepts == (METHOD["borehole-and-mine"],)
        assert PROBE_SENSING.concepts == (METHOD["probe-sensing"],)

    def test_each_domain_is_scored_by_the_scoring_the_scores_name(self) -> None:
        assert (BOREHOLE.scoring, PROBE_SENSING.scoring) == (
            "borehole and mine",
            "probe sensing",
        )
