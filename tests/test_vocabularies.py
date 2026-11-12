from pathlib import Path

import pytest
import responses
from example_site import EXAMPLE_FILES, publish
from frictionless import Schema
from rdflib import RDF, Graph, URIRef
from rdflib.namespace import SKOS
from requests_cache import CachedSession

from ghfdb.vocabularies import (
    AllowedValue,
    MissingSchemeError,
    Vocabularies,
    caching_session,
)

COLOURS = "https://example.test/vocabularies/colours"
SHAPES = "https://example.test/vocabularies/shapes"
ROCKS = "https://example.test/schemes/rocks"
ROCKS_FILE = "https://example.test/downloads/rocks.rdf"
RDF_XML = "application/rdf+xml"


def vocabulary(
    scheme: str, collection: str | None = None, term_form: str = "label"
) -> dict[str, str | None]:
    return {"scheme": scheme, "collection": collection, "termForm": term_form}


def published_elsewhere(
    collection: str | None = None, term_form: str = "localName"
) -> dict[str, str | None]:
    return vocabulary(ROCKS, collection, term_form) | {
        "download": ROCKS_FILE,
        "downloadFormat": RDF_XML,
    }


def publish_rocks(web: responses.RequestsMock, body: bytes | None = None) -> None:
    web.get(
        ROCKS_FILE,
        body=(EXAMPLE_FILES / "rocks.rdf").read_bytes() if body is None else body,
        headers={"ETag": '"one"', "Cache-Control": "max-age=0"},
    )


@pytest.fixture
def vocabularies(web: responses.RequestsMock, tmp_path: Path) -> Vocabularies:
    publish(web, "colours")
    publish(web, "shapes")
    return Vocabularies(caching_session(tmp_path))


class TestCachingSession:
    def test_keeps_its_files_in_the_directory_it_is_given(self, tmp_path: Path) -> None:
        session = caching_session(tmp_path)

        assert isinstance(session, CachedSession)
        assert Path(session.cache.cache_dir) == tmp_path  # type: ignore[attr-defined]

    def test_keeps_its_files_in_the_user_cache_directory_otherwise(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr(
            "ghfdb.vocabularies.user_cache_dir", lambda _: str(tmp_path)
        )

        session = caching_session()

        assert Path(session.cache.cache_dir) == tmp_path / "vocabularies"  # type: ignore[attr-defined]


class TestDownload:
    def test_a_scheme_is_downloaded_from_its_identifier_with_ttl_added(
        self, web: responses.RequestsMock, vocabularies: Vocabularies
    ) -> None:
        graph = vocabularies.graph(COLOURS)

        assert (URIRef(COLOURS), RDF.type, SKOS.ConceptScheme) in graph
        assert [call.request.url for call in web.calls] == [f"{COLOURS}.ttl"]

    def test_a_file_is_downloaded_once_per_object(
        self, web: responses.RequestsMock, vocabularies: Vocabularies
    ) -> None:
        vocabularies.graph(COLOURS)
        vocabularies.graph(COLOURS)

        assert len(web.calls) == 1

    def test_an_unchanged_file_is_checked_with_its_etag_and_read_from_the_cache(
        self, web: responses.RequestsMock, tmp_path: Path
    ) -> None:
        publish(web, "colours")
        publish(web, "colours", status=304)
        session = caching_session(tmp_path)
        Vocabularies(session).graph(COLOURS)

        graph = Vocabularies(session).graph(COLOURS)

        assert web.calls[1].request.headers["If-None-Match"] == '"one"'
        assert (URIRef(COLOURS), RDF.type, SKOS.ConceptScheme) in graph

    def test_a_changed_file_is_downloaded_again(
        self, web: responses.RequestsMock, tmp_path: Path
    ) -> None:
        publish(web, "colours")
        publish(web, "colours", etag='"two"')
        session = caching_session(tmp_path)
        Vocabularies(session).graph(COLOURS)

        Vocabularies(session).graph(COLOURS)

        assert len(web.calls) == 2
        assert web.calls[1].request.headers["If-None-Match"] == '"one"'

    def test_the_cached_file_is_used_when_the_server_cannot_be_reached(
        self, web: responses.RequestsMock, tmp_path: Path
    ) -> None:
        publish(web, "colours")
        publish(web, "colours", body=ConnectionError("offline"))
        session = caching_session(tmp_path)
        Vocabularies(session).graph(COLOURS)

        graph = Vocabularies(session).graph(COLOURS)

        assert (URIRef(COLOURS), RDF.type, SKOS.ConceptScheme) in graph

    def test_a_scheme_that_cannot_be_downloaded_is_reported(
        self, web: responses.RequestsMock, tmp_path: Path
    ) -> None:
        publish(web, "colours", body=ConnectionError("offline"))

        with pytest.raises(OSError):
            Vocabularies(caching_session(tmp_path)).graph(COLOURS)

    def test_a_missing_file_is_reported(
        self, web: responses.RequestsMock, tmp_path: Path
    ) -> None:
        publish(web, "fabrics", body=b"", status=404)

        with pytest.raises(OSError, match="404"):
            Vocabularies(caching_session(tmp_path)).graph(
                "https://example.test/vocabularies/fabrics"
            )

    def test_something_that_is_not_turtle_is_refused(
        self, web: responses.RequestsMock, tmp_path: Path
    ) -> None:
        publish(web, "colours", body=b"<html>not turtle")

        with pytest.raises(OSError, match="not Turtle"):
            Vocabularies(caching_session(tmp_path)).graph(COLOURS)


class TestDownloadElsewhere:
    def test_a_file_sent_with_no_cache_headers_is_kept_for_when_the_server_is_down(
        self, web: responses.RequestsMock, tmp_path: Path
    ) -> None:
        body = (EXAMPLE_FILES / "rocks.rdf").read_bytes()
        web.get(ROCKS_FILE, body=body)
        web.get(ROCKS_FILE, body=ConnectionError("offline"))
        session = caching_session(tmp_path)
        Vocabularies(session).allowed_values(published_elsewhere())

        values = Vocabularies(session).allowed_values(published_elsewhere())

        assert {value.label for value in values} == {
            "volcanic glass",
            "sandstone",
            "boundary",
        }

    def test_a_scheme_not_published_at_its_identifier_is_read_from_the_named_file(
        self, web: responses.RequestsMock, tmp_path: Path
    ) -> None:
        publish_rocks(web)

        values = Vocabularies(caching_session(tmp_path)).allowed_values(
            published_elsewhere()
        )

        assert [call.request.url for call in web.calls] == [ROCKS_FILE]
        assert {value.label for value in values} == {
            "volcanic glass",
            "sandstone",
            "boundary",
        }

    def test_a_file_that_is_not_in_the_named_format_is_refused(
        self, web: responses.RequestsMock, tmp_path: Path
    ) -> None:
        publish_rocks(web, b"@prefix skos: <http://www.w3.org/2004/02/skos/core#> .")

        with pytest.raises(OSError, match="not RDF/XML"):
            Vocabularies(caching_session(tmp_path)).allowed_values(
                published_elsewhere()
            )

    def test_a_collection_gives_the_concepts_of_the_collections_it_holds(
        self, web: responses.RequestsMock, tmp_path: Path
    ) -> None:
        publish_rocks(web)

        values = Vocabularies(caching_session(tmp_path)).allowed_values(
            published_elsewhere("https://example.test/rocks/all")
        )

        assert {value.uri for value in values} == {
            "https://example.test/rocks/volcanic_glass",
            "https://example.test/rocks/sandstone",
        }

    def test_the_local_name_form_writes_the_last_segment_of_the_uri_without_brackets(
        self, web: responses.RequestsMock, tmp_path: Path
    ) -> None:
        publish_rocks(web)

        values = Vocabularies(caching_session(tmp_path)).allowed_values(
            published_elsewhere("https://example.test/rocks/igneous")
        )

        assert values == (
            AllowedValue(
                "volcanic_glass",
                "volcanic glass",
                "https://example.test/rocks/volcanic_glass",
                None,
            ),
        )

    def test_a_scheme_read_from_elsewhere_adds_no_release_and_breaks_nothing(
        self, web: responses.RequestsMock, tmp_path: Path
    ) -> None:
        publish(web, "colours")
        publish_rocks(web)
        vocabularies = Vocabularies(caching_session(tmp_path))
        vocabularies.allowed_values(published_elsewhere())
        vocabularies.graph(COLOURS)

        assert vocabularies.releases() == ["https://doi.org/10.0000/test.1"]


class TestAllowedValues:
    def test_a_scheme_gives_every_one_of_its_concepts(
        self, vocabularies: Vocabularies
    ) -> None:
        values = vocabularies.allowed_values(vocabulary(COLOURS))

        assert {value.uri for value in values} == {
            f"{COLOURS}/red",
            f"{COLOURS}/orange",
            f"{COLOURS}/blue",
            f"{COLOURS}/green",
        }

    def test_a_collection_gives_only_its_members(
        self, vocabularies: Vocabularies
    ) -> None:
        values = vocabularies.allowed_values(vocabulary(COLOURS, f"{COLOURS}/warm"))

        assert {value.uri for value in values} == {
            f"{COLOURS}/red",
            f"{COLOURS}/orange",
        }

    def test_an_ordered_collection_keeps_its_order(
        self, vocabularies: Vocabularies
    ) -> None:
        values = vocabularies.allowed_values(vocabulary(COLOURS, f"{COLOURS}/spectrum"))

        assert [value.term for value in values] == ["[red]", "[Orange]", "[green]"]

    def test_a_value_carries_its_english_label_uri_and_notation(
        self, vocabularies: Vocabularies
    ) -> None:
        values = vocabularies.allowed_values(vocabulary(COLOURS, f"{COLOURS}/warm"))

        assert AllowedValue("[red]", "red", f"{COLOURS}/red", "rd") in values

    def test_a_concept_without_a_notation_has_none(
        self, vocabularies: Vocabularies
    ) -> None:
        values = vocabularies.allowed_values(vocabulary(COLOURS))

        blue = next(value for value in values if value.label == "Blue")
        assert blue.notation is None

    def test_notation_form_uses_the_notation_where_the_concept_has_one(
        self, vocabularies: Vocabularies
    ) -> None:
        values = vocabularies.allowed_values(vocabulary(COLOURS, None, "notation"))

        assert {value.term for value in values} == {"[rd]", "[or]", "[Blue]", "[green]"}

    def test_label_form_ignores_alternative_and_hidden_labels(
        self, vocabularies: Vocabularies
    ) -> None:
        values = vocabularies.allowed_values(vocabulary(COLOURS))

        assert {value.term for value in values} == {
            "[red]",
            "[Orange]",
            "[Blue]",
            "[green]",
        }

    def test_values_are_sorted_by_term_ignoring_case(
        self, vocabularies: Vocabularies
    ) -> None:
        values = vocabularies.allowed_values(vocabulary(COLOURS))

        assert [value.term for value in values] == [
            "[Blue]",
            "[green]",
            "[Orange]",
            "[red]",
        ]

    def test_a_scheme_the_file_does_not_define_is_named_in_the_error(
        self, web: responses.RequestsMock, vocabularies: Vocabularies
    ) -> None:
        publish(web, "colours", base="https://example.test/other")

        with pytest.raises(MissingSchemeError, match="other/colours"):
            vocabularies.allowed_values(
                vocabulary("https://example.test/other/colours")
            )

    def test_a_collection_the_file_does_not_define_is_named_in_the_error(
        self, vocabularies: Vocabularies
    ) -> None:
        with pytest.raises(MissingSchemeError, match="colours/cool"):
            vocabularies.allowed_values(vocabulary(COLOURS, f"{COLOURS}/cool"))

    def test_a_concept_without_an_english_label_is_an_error(
        self, web: responses.RequestsMock, tmp_path: Path
    ) -> None:
        publish(
            web,
            "shapes",
            body=(
                "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .\n"
                f"<{SHAPES}> a skos:ConceptScheme .\n"
                f"<{SHAPES}/round> a skos:Concept ;\n"
                f"  skos:inScheme <{SHAPES}> ;\n"
                '  skos:prefLabel "rund"@de .\n'
            ).encode(),
        )

        with pytest.raises(MissingSchemeError, match="round"):
            Vocabularies(caching_session(tmp_path)).allowed_values(vocabulary(SHAPES))


class TestReleases:
    def test_no_scheme_read_gives_no_release(self, tmp_path: Path) -> None:
        assert Vocabularies(caching_session(tmp_path)).releases() == []

    def test_a_release_shared_by_the_schemes_read_is_given_once(
        self, vocabularies: Vocabularies
    ) -> None:
        vocabularies.graph(COLOURS)
        vocabularies.graph(SHAPES)

        assert vocabularies.releases() == ["https://doi.org/10.0000/test.1"]

    def test_the_releases_of_every_scheme_read_are_given_sorted(
        self, web: responses.RequestsMock, tmp_path: Path
    ) -> None:
        publish(web, "colours")
        later = (EXAMPLE_FILES / "shapes.ttl").read_bytes()
        publish(web, "shapes", body=later.replace(b"test.1", b"test.0"))
        vocabularies = Vocabularies(caching_session(tmp_path))
        vocabularies.graph(COLOURS)
        vocabularies.graph(SHAPES)

        assert vocabularies.releases() == [
            "https://doi.org/10.0000/test.0",
            "https://doi.org/10.0000/test.1",
        ]

    def test_a_scheme_not_read_adds_no_release(
        self, vocabularies: Vocabularies
    ) -> None:
        vocabularies.graph(SHAPES)

        assert vocabularies.releases() == ["https://doi.org/10.0000/test.1"]
        assert COLOURS not in vocabularies.graphs


# The tests below read the vocabularies as currently published at their permanent
# identifiers. The cache of a test session starts empty (see conftest.py), so they fail
# when the vocabularies change beneath the schema.
class TestPublishedVocabularies:
    def test_every_scheme_and_collection_the_schema_names_is_defined_where_published(
        self, schema: Schema, published_vocabularies: Vocabularies
    ) -> None:
        for field in schema.fields:
            named = field.custom["vocabulary"]
            if named is None:
                continue
            graph: Graph = published_vocabularies.graph(named["scheme"])
            scheme = URIRef(named["scheme"])
            assert (scheme, RDF.type, SKOS.ConceptScheme) in graph, field.name
            if named["collection"] is not None:
                collection = URIRef(named["collection"])
                kinds = set(graph.objects(collection, RDF.type))
                assert kinds & {SKOS.Collection, SKOS.OrderedCollection}, field.name

    def test_every_vocabulary_field_has_allowed_values(self, schema: Schema) -> None:
        bound = [f for f in schema.fields if f.custom["vocabulary"] is not None]

        assert len(bound) == 27
        assert all(field.constraints.get("enum") for field in bound)


class TestExternalVocabularies:
    def test_lithology_terms_are_the_local_names_of_the_cgi_concepts(
        self, schema: Schema
    ) -> None:
        enum = schema.get_field("C25").constraints["enum"]

        assert "acidic_igneous_material" in enum
        assert not any(term.startswith("[") for term in enum)

    def test_stratigraphic_age_terms_are_geochronologic_eras_only(
        self, schema: Schema
    ) -> None:
        enum = schema.get_field("C26").constraints["enum"]

        assert "LowerCretaceous" in enum
        assert not any(term.startswith("Base") for term in enum)
