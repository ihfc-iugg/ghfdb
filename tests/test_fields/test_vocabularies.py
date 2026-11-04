import os
import time
from io import BytesIO
from pathlib import Path
from typing import Literal
from urllib.error import HTTPError

import pytest
from rdflib import RDF, Graph, URIRef
from rdflib.namespace import SKOS

from ghfdb.fields import (
    AllowedValue,
    FieldSchema,
    MissingSchemeError,
    Vocabularies,
    VocabularyBinding,
)
from ghfdb.fields.vocabularies import MAX_AGE_SECONDS, cache_directory

FIXTURES = Path(__file__).parent / "vocabularies"
COLOURS = "https://example.test/vocabularies/colours"
SHAPES = "https://example.test/vocabularies/shapes"


def binding(
    scheme: str,
    collection: str | None = None,
    term_form: Literal["label", "notation"] = "label",
) -> VocabularyBinding:
    return VocabularyBinding(scheme, collection, term_form)


def published(tmp_path: Path) -> Path:
    """Publish the test schemes in a local directory and return their address.

    A scheme is published at its identifier with ``.ttl`` added, so a scheme whose
    identifier is a ``file:`` address is downloaded from that directory.
    """
    site = tmp_path / "site"
    site.mkdir()
    for path in FIXTURES.glob("*.ttl"):
        (site / path.name).write_bytes(path.read_bytes())
    return site


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
    def test_a_missing_file_is_downloaded_from_the_identifier_with_ttl_added(
        self, tmp_path: Path
    ) -> None:
        site = published(tmp_path)
        cache = tmp_path / "cache"
        scheme = (site / "colours").as_uri()

        graph = Vocabularies(cache).graph(scheme)

        assert (cache / "colours.ttl").read_bytes() == (
            site / "colours.ttl"
        ).read_bytes()
        assert (URIRef(COLOURS), RDF.type, SKOS.ConceptScheme) in graph

    def test_a_cached_file_is_read_without_downloading_it_again(
        self, tmp_path: Path
    ) -> None:
        cache = tmp_path / "cache"
        cache.mkdir()
        (cache / "colours.ttl").write_bytes((FIXTURES / "colours.ttl").read_bytes())
        missing = (tmp_path / "nowhere" / "colours").as_uri()

        graph = Vocabularies(cache).graph(missing)

        assert (URIRef(COLOURS), RDF.type, SKOS.ConceptScheme) in graph

    def test_a_file_older_than_a_week_is_downloaded_again(self, tmp_path: Path) -> None:
        site = published(tmp_path)
        cache = tmp_path / "cache"
        cache.mkdir()
        stale = cache / "colours.ttl"
        stale.write_text("")
        old = time.time() - MAX_AGE_SECONDS - 60
        os.utime(stale, (old, old))

        Vocabularies(cache).graph((site / "colours").as_uri())

        assert stale.read_bytes() == (site / "colours.ttl").read_bytes()

    def test_an_old_file_is_kept_when_the_download_fails(self, tmp_path: Path) -> None:
        cache = tmp_path / "cache"
        cache.mkdir()
        old_file = cache / "colours.ttl"
        old_file.write_bytes((FIXTURES / "colours.ttl").read_bytes())
        old = time.time() - MAX_AGE_SECONDS - 60
        os.utime(old_file, (old, old))
        offline = (tmp_path / "nowhere" / "colours").as_uri()

        graph = Vocabularies(cache).graph(offline)

        assert (URIRef(COLOURS), RDF.type, SKOS.ConceptScheme) in graph

    def test_a_scheme_that_cannot_be_downloaded_leaves_nothing_in_the_cache(
        self, tmp_path: Path
    ) -> None:
        cache = tmp_path / "cache"

        with pytest.raises(OSError):
            Vocabularies(cache).graph((tmp_path / "nowhere" / "colours").as_uri())

        assert not list(cache.glob("*"))

    def test_something_that_is_not_turtle_is_refused_and_not_cached(
        self, tmp_path: Path
    ) -> None:
        site = published(tmp_path)
        (site / "colours.ttl").write_text("<html>not turtle")
        cache = tmp_path / "cache"

        with pytest.raises(OSError, match="not Turtle"):
            Vocabularies(cache).graph((site / "colours").as_uri())

        assert not list(cache.glob("*"))


class TestServerErrors:
    @staticmethod
    def failing(codes: list[int]):  # type: ignore[no-untyped-def]
        def urlopen(address: str, timeout: float) -> BytesIO:
            if codes:
                raise HTTPError(address, codes.pop(0), "failed", None, None)  # type: ignore[arg-type]
            return BytesIO((FIXTURES / "colours.ttl").read_bytes())

        return urlopen

    def test_a_server_error_is_tried_again(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr(
            "ghfdb.fields.vocabularies.urlopen", self.failing([502, 503])
        )
        monkeypatch.setattr("time.sleep", lambda seconds: None)

        graph = Vocabularies(tmp_path).graph(COLOURS)

        assert (URIRef(COLOURS), RDF.type, SKOS.ConceptScheme) in graph

    def test_a_server_that_keeps_failing_is_reported(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr(
            "ghfdb.fields.vocabularies.urlopen", self.failing([502, 502, 502])
        )
        monkeypatch.setattr("time.sleep", lambda seconds: None)

        with pytest.raises(HTTPError):
            Vocabularies(tmp_path).graph(COLOURS)

    def test_a_missing_file_is_not_tried_again(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        codes = [404, 502]
        monkeypatch.setattr("ghfdb.fields.vocabularies.urlopen", self.failing(codes))

        with pytest.raises(HTTPError):
            Vocabularies(tmp_path).graph(COLOURS)

        assert codes == [502]


class TestAllowedValues:
    vocabularies = Vocabularies(FIXTURES)

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

    def test_a_concept_without_an_english_label_is_an_error(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "shapes.ttl").write_text(
            "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .\n"
            f"<{SHAPES}> a skos:ConceptScheme .\n"
            f"<{SHAPES}/round> a skos:Concept ;\n"
            f"  skos:inScheme <{SHAPES}> ;\n"
            '  skos:prefLabel "rund"@de .\n'
        )

        with pytest.raises(MissingSchemeError, match="round"):
            Vocabularies(tmp_path).allowed_values(binding(SHAPES))


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
