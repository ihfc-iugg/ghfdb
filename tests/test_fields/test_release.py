import zipfile
from pathlib import Path
from typing import Literal
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, build_opener

import pytest
from rdflib import RDF, Graph
from rdflib.namespace import DCTERMS, SKOS

from ghfdb.fields import (
    AllowedValue,
    FieldSchema,
    MissingSchemeError,
    ReleaseFiles,
    VocabularyBinding,
    VocabularyRelease,
)
from ghfdb.fields.release import ARCHIVE, cache_directory, download

RELEASES = Path(__file__).parent / "releases"
COLOURS = "https://example.test/vocabularies/colours"
VERSION = "9999.1"


def binding(
    scheme_name: str,
    collection_name: str | None = None,
    term_form: Literal["label", "notation"] = "label",
) -> VocabularyBinding:
    return VocabularyBinding(scheme_name, collection_name, term_form)


def archive_path(tmp_path: Path) -> Path:
    return tmp_path / "repository" / "releases" / "download" / f"v{VERSION}" / ARCHIVE


def published(tmp_path: Path, files: dict[str, bytes]) -> VocabularyRelease:
    """Publish a release holding the given archive members in a local directory."""
    archive = archive_path(tmp_path)
    archive.parent.mkdir(parents=True)
    with zipfile.ZipFile(archive, "w") as zipped:
        for name, content in files.items():
            zipped.writestr(name, content)
    repository = (tmp_path / "repository").as_uri()
    return VocabularyRelease(VERSION, "10.0000/test.1", repository)


def release_members() -> dict[str, bytes]:
    return {
        f"ihfc-vocabularies-{VERSION}/vocabularies/{path.name}": path.read_bytes()
        for path in (RELEASES / VERSION).iterdir()
    }


class TestVocabularyRelease:
    def test_the_archive_is_the_full_zip_of_the_tagged_release(self) -> None:
        release = VocabularyRelease("2026.1", "10.0000/x", "https://example.test/repo")

        assert release.archive_url == (
            "https://example.test/repo/releases/download/v2026.1/vocabularies-full.zip"
        )


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


class TestFetch:
    def test_downloads_the_turtle_files_into_a_directory_named_for_the_version(
        self, tmp_path: Path
    ) -> None:
        release = published(tmp_path, release_members())
        cache = tmp_path / "cache"

        files = ReleaseFiles.fetch(release, cache)

        assert files.directory == cache / VERSION
        assert sorted(path.name for path in files.directory.iterdir()) == [
            "colours.ttl",
            "shapes.ttl",
        ]

    def test_leaves_out_everything_that_is_not_turtle(self, tmp_path: Path) -> None:
        members = release_members() | {"x/colours.nt": b"", "x/LICENSE": b"-"}
        release = published(tmp_path, members)

        files = ReleaseFiles.fetch(release, tmp_path / "cache")

        assert {path.suffix for path in files.directory.iterdir()} == {".ttl"}

    def test_reads_a_cached_release_without_downloading_it_again(
        self, tmp_path: Path
    ) -> None:
        release = published(tmp_path, release_members())
        cache = tmp_path / "cache"
        ReleaseFiles.fetch(release, cache)
        archive_path(tmp_path).unlink()

        files = ReleaseFiles.fetch(release, cache)

        assert (files.directory / "colours.ttl").is_file()

    def test_a_release_that_cannot_be_downloaded_leaves_nothing_in_the_cache(
        self, tmp_path: Path
    ) -> None:
        repository = (tmp_path / "none").as_uri()
        release = VocabularyRelease(VERSION, "10.0000/test.1", repository)
        cache = tmp_path / "cache"

        with pytest.raises(OSError):
            ReleaseFiles.fetch(release, cache)

        assert list(cache.iterdir()) == []

    def test_an_archive_without_turtle_files_is_refused(self, tmp_path: Path) -> None:
        release = published(tmp_path, {"x/LICENSE": b"-"})
        target = tmp_path / "cache" / VERSION

        with pytest.raises(OSError, match="no Turtle files"):
            download(release, target)

        assert not target.exists()

    def test_something_that_is_not_a_zip_archive_is_refused(
        self, tmp_path: Path
    ) -> None:
        release = published(tmp_path, {})
        archive_path(tmp_path).write_bytes(b"not a zip")

        with pytest.raises(OSError, match="not a zip archive"):
            download(release, tmp_path / "cache" / VERSION)


class TestReleaseFiles:
    files = ReleaseFiles(RELEASES / VERSION)

    def test_a_scheme_gives_every_one_of_its_concepts(self) -> None:
        values = self.files.allowed_values(binding("colours"))

        assert {value.uri for value in values} == {
            f"{COLOURS}/red",
            f"{COLOURS}/orange",
            f"{COLOURS}/blue",
            f"{COLOURS}/green",
        }

    def test_a_collection_gives_only_its_members(self) -> None:
        values = self.files.allowed_values(binding("colours", "warm"))

        assert {value.uri for value in values} == {
            f"{COLOURS}/red",
            f"{COLOURS}/orange",
        }

    def test_an_ordered_collection_keeps_its_order(self) -> None:
        values = self.files.allowed_values(binding("colours", "spectrum"))

        assert [value.term for value in values] == ["[red]", "[Orange]", "[green]"]

    def test_a_value_carries_its_english_label_uri_and_notation(self) -> None:
        values = self.files.allowed_values(binding("colours", "warm"))

        assert AllowedValue("[red]", "red", f"{COLOURS}/red", "rd") in values

    def test_a_concept_without_a_notation_has_none(self) -> None:
        values = self.files.allowed_values(binding("colours"))

        blue = next(value for value in values if value.label == "Blue")
        assert blue.notation is None

    def test_notation_form_uses_the_notation_where_the_concept_has_one(self) -> None:
        values = self.files.allowed_values(binding("colours", term_form="notation"))

        assert {value.term for value in values} == {"[rd]", "[or]", "[Blue]", "[green]"}

    def test_label_form_ignores_alternative_and_hidden_labels(self) -> None:
        values = self.files.allowed_values(binding("colours"))

        assert {value.term for value in values} == {
            "[red]",
            "[Orange]",
            "[Blue]",
            "[green]",
        }

    def test_values_are_sorted_by_term_ignoring_case(self) -> None:
        values = self.files.allowed_values(binding("colours"))

        assert [value.term for value in values] == [
            "[Blue]",
            "[green]",
            "[Orange]",
            "[red]",
        ]

    def test_an_unknown_scheme_name_is_named_in_the_error(self) -> None:
        with pytest.raises(MissingSchemeError, match="fabrics"):
            self.files.allowed_values(binding("fabrics"))

    def test_an_unknown_collection_name_is_named_in_the_error(self) -> None:
        with pytest.raises(MissingSchemeError, match="cool"):
            self.files.allowed_values(binding("colours", "cool"))

    def test_a_collection_of_another_scheme_is_not_found(self) -> None:
        with pytest.raises(MissingSchemeError, match="warm"):
            self.files.allowed_values(binding("shapes", "warm"))

    def test_a_concept_without_an_english_label_is_an_error(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "shapes.ttl").write_text(
            "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .\n"
            "<https://example.test/v/shapes> a skos:ConceptScheme .\n"
            "<https://example.test/v/shapes/round> a skos:Concept ;\n"
            "  skos:inScheme <https://example.test/v/shapes> ;\n"
            '  skos:prefLabel "rund"@de .\n'
        )

        with pytest.raises(MissingSchemeError, match="round"):
            ReleaseFiles(tmp_path).allowed_values(binding("shapes"))


# The tests below use the real published release, which is downloaded into the cache
# the first time they run. They fail when the vocabularies change beneath the schema.
SHIPPED = FieldSchema.load()


def newest_published_version(repository: str) -> str:
    """Ask GitHub which release the repository calls its latest.

    GitHub answers the address of the latest release with a redirect to its tag, so
    the answer is read from the redirect without calling the rate-limited API.
    """

    class StopAtRedirect(HTTPRedirectHandler):
        def redirect_request(self, *args: object, **kwargs: object) -> None:
            return None

    try:
        build_opener(StopAtRedirect).open(f"{repository}/releases/latest", timeout=60)
    except HTTPError as error:
        location = error.headers["Location"]
        if error.code in (301, 302, 303, 307, 308) and "/releases/tag/" in location:
            return location.rsplit("/", 1)[-1].removeprefix("v")
        raise
    raise AssertionError(f"{repository} has no latest release")


def version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


class TestPublishedRelease:
    def test_the_vocabularies_have_published_nothing_newer_than_the_stated_release(
        self,
    ) -> None:
        release = SHIPPED.release

        newest = newest_published_version(release.repository)

        assert version_key(newest) <= version_key(release.version), (
            f"The vocabularies have published release {newest}, but the schema "
            f"states {release.version}. See docs/contributing/vocabulary-release.md."
        )

    def test_the_stated_doi_is_the_one_the_release_files_give(self) -> None:
        directory = ReleaseFiles.fetch(SHIPPED.release).directory
        graph = Graph()
        for path in directory.glob("*.ttl"):
            graph.parse(path, format="turtle")

        dois = {
            str(doi).removeprefix("https://doi.org/")
            for scheme in graph.subjects(RDF.type, SKOS.ConceptScheme)
            for doi in graph.objects(scheme, DCTERMS.isPartOf)
        }

        assert dois == {SHIPPED.release.doi}

    def test_every_vocabulary_field_has_allowed_values_from_the_release(self) -> None:
        bound = [field for field in SHIPPED if field.vocabulary is not None]

        assert len(bound) == 25
        assert all(field.allowed_values for field in bound)
