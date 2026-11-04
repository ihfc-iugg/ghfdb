from pathlib import Path
from typing import Literal

import pytest
from fakes import FakeSite, fake_session
from rdflib import RDF, Graph, URIRef
from rdflib.namespace import SKOS
from requests_cache import CachedSession

from ghfdb.fields import (
    AllowedValue,
    FieldSchema,
    MissingSchemeError,
    Vocabularies,
    VocabularyBinding,
)
from ghfdb.fields.vocabularies import cache_directory, caching_session

COLOURS = "https://example.test/vocabularies/colours"
SHAPES = "https://example.test/vocabularies/shapes"


def binding(
    scheme: str,
    collection: str | None = None,
    term_form: Literal["label", "notation"] = "label",
) -> VocabularyBinding:
    return VocabularyBinding(scheme, collection, term_form)


def vocabularies() -> tuple[Vocabularies, FakeSite]:
    site = FakeSite()
    return Vocabularies(fake_session(site)), site


class TestCacheDirectory:
    def test_is_the_directory_the_environment_names(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("GHFDB_VOCABULARY_CACHE", str(tmp_path))

        assert cache_directory() == tmp_path

    def test_is_inside_the_user_cache_directory_otherwise(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.delenv("GHFDB_VOCABULARY_CACHE", raising=False)
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))

        assert cache_directory() == tmp_path / "ghfdb" / "vocabularies"


class TestDownload:
    def test_a_scheme_is_downloaded_from_its_identifier_with_ttl_added(self) -> None:
        vocabularies_, site = vocabularies()

        graph = vocabularies_.graph(COLOURS)

        assert (URIRef(COLOURS), RDF.type, SKOS.ConceptScheme) in graph
        assert [request.url for request in site.requests] == [f"{COLOURS}.ttl"]

    def test_a_file_is_downloaded_once_per_object(self) -> None:
        vocabularies_, site = vocabularies()

        vocabularies_.graph(COLOURS)
        vocabularies_.graph(COLOURS)

        assert len(site.requests) == 1

    def test_an_unchanged_file_is_checked_with_its_etag_and_read_from_the_cache(
        self,
    ) -> None:
        site = FakeSite()
        session = fake_session(site)
        Vocabularies(session).graph(COLOURS)

        graph = Vocabularies(session).graph(COLOURS)

        assert site.requests[1].headers["If-None-Match"] == site.etag
        assert (URIRef(COLOURS), RDF.type, SKOS.ConceptScheme) in graph

    def test_a_changed_file_is_downloaded_again(self) -> None:
        site = FakeSite()
        session = fake_session(site)
        Vocabularies(session).graph(COLOURS)
        site.etag = '"two"'

        Vocabularies(session).graph(COLOURS)

        assert len(site.requests) == 2
        assert site.requests[1].headers["If-None-Match"] == '"one"'

    def test_the_cached_file_is_used_when_the_server_cannot_be_reached(self) -> None:
        site = FakeSite()
        session = fake_session(site)
        Vocabularies(session).graph(COLOURS)
        site.failure = ConnectionError("offline")

        graph = Vocabularies(session).graph(COLOURS)

        assert (URIRef(COLOURS), RDF.type, SKOS.ConceptScheme) in graph

    def test_a_scheme_that_cannot_be_downloaded_is_reported(self) -> None:
        vocabularies_, site = vocabularies()
        site.failure = ConnectionError("offline")

        with pytest.raises(OSError):
            vocabularies_.graph(COLOURS)

    def test_a_missing_file_is_reported(self) -> None:
        vocabularies_, _ = vocabularies()

        with pytest.raises(OSError, match="404"):
            vocabularies_.graph("https://example.test/vocabularies/fabrics")

    def test_something_that_is_not_turtle_is_refused(self) -> None:
        vocabularies_, site = vocabularies()
        site.override["colours.ttl"] = b"<html>not turtle"

        with pytest.raises(OSError, match="not Turtle"):
            vocabularies_.graph(COLOURS)

    def test_the_default_session_keeps_its_files_in_the_cache_directory(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("GHFDB_VOCABULARY_CACHE", str(tmp_path))

        session = caching_session()

        assert isinstance(session, CachedSession)
        assert Path(session.cache.cache_dir) == tmp_path  # type: ignore[attr-defined]


class TestAllowedValues:
    vocabularies = Vocabularies(fake_session(FakeSite()))

    def test_a_scheme_gives_every_one_of_its_concepts(self) -> None:
        values = self.vocabularies.allowed_values(binding(COLOURS))

        assert {value.uri for value in values} == {
            f"{COLOURS}/red",
            f"{COLOURS}/orange",
            f"{COLOURS}/blue",
            f"{COLOURS}/green",
        }

    def test_a_collection_gives_only_its_members(self) -> None:
        values = self.vocabularies.allowed_values(binding(COLOURS, f"{COLOURS}/warm"))

        assert {value.uri for value in values} == {
            f"{COLOURS}/red",
            f"{COLOURS}/orange",
        }

    def test_an_ordered_collection_keeps_its_order(self) -> None:
        values = self.vocabularies.allowed_values(
            binding(COLOURS, f"{COLOURS}/spectrum")
        )

        assert [value.term for value in values] == ["[red]", "[Orange]", "[green]"]

    def test_a_value_carries_its_english_label_uri_and_notation(self) -> None:
        values = self.vocabularies.allowed_values(binding(COLOURS, f"{COLOURS}/warm"))

        assert AllowedValue("[red]", "red", f"{COLOURS}/red", "rd") in values

    def test_a_concept_without_a_notation_has_none(self) -> None:
        values = self.vocabularies.allowed_values(binding(COLOURS))

        blue = next(value for value in values if value.label == "Blue")
        assert blue.notation is None

    def test_notation_form_uses_the_notation_where_the_concept_has_one(self) -> None:
        values = self.vocabularies.allowed_values(binding(COLOURS, None, "notation"))

        assert {value.term for value in values} == {"[rd]", "[or]", "[Blue]", "[green]"}

    def test_label_form_ignores_alternative_and_hidden_labels(self) -> None:
        values = self.vocabularies.allowed_values(binding(COLOURS))

        assert {value.term for value in values} == {
            "[red]",
            "[Orange]",
            "[Blue]",
            "[green]",
        }

    def test_values_are_sorted_by_term_ignoring_case(self) -> None:
        values = self.vocabularies.allowed_values(binding(COLOURS))

        assert [value.term for value in values] == [
            "[Blue]",
            "[green]",
            "[Orange]",
            "[red]",
        ]

    def test_a_scheme_the_file_does_not_define_is_named_in_the_error(self) -> None:
        with pytest.raises(MissingSchemeError, match="other/colours"):
            self.vocabularies.allowed_values(
                binding("https://example.test/other/colours")
            )

    def test_a_collection_the_file_does_not_define_is_named_in_the_error(self) -> None:
        with pytest.raises(MissingSchemeError, match="colours/cool"):
            self.vocabularies.allowed_values(binding(COLOURS, f"{COLOURS}/cool"))

    def test_a_concept_without_an_english_label_is_an_error(self) -> None:
        vocabularies_, site = vocabularies()
        site.override["shapes.ttl"] = (
            "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .\n"
            f"<{SHAPES}> a skos:ConceptScheme .\n"
            f"<{SHAPES}/round> a skos:Concept ;\n"
            f"  skos:inScheme <{SHAPES}> ;\n"
            '  skos:prefLabel "rund"@de .\n'
        ).encode()

        with pytest.raises(MissingSchemeError, match="round"):
            vocabularies_.allowed_values(binding(SHAPES))


# The tests below read the vocabularies as currently published at their permanent
# identifiers. The cache of a test session starts empty (see conftest.py), so they fail
# when the vocabularies change beneath the schema.
SHIPPED = FieldSchema.load()


class TestPublishedVocabularies:
    def test_every_scheme_and_collection_the_schema_names_is_defined_where_published(
        self,
    ) -> None:
        vocabularies = Vocabularies()

        for field in SHIPPED:
            if field.vocabulary is None:
                continue
            graph: Graph = vocabularies.graph(field.vocabulary.scheme)
            scheme = URIRef(field.vocabulary.scheme)
            assert (scheme, RDF.type, SKOS.ConceptScheme) in graph, field.code
            if field.vocabulary.collection is not None:
                collection = URIRef(field.vocabulary.collection)
                kinds = set(graph.objects(collection, RDF.type))
                assert kinds & {SKOS.Collection, SKOS.OrderedCollection}, field.code

    def test_every_vocabulary_field_has_allowed_values(self) -> None:
        bound = [field for field in SHIPPED if field.vocabulary is not None]

        assert len(bound) == 25
        assert all(field.allowed_values for field in bound)
