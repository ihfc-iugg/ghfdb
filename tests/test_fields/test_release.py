from pathlib import Path
from typing import Literal

import pytest

from ghfdb.fields.release import MissingSchemeError, ReleaseFiles
from ghfdb.fields.schema import AllowedValue, VocabularyBinding, VocabularyRelease

RELEASES = Path(__file__).parent / "releases"
COLOURS = "https://example.test/vocabularies/colours"


def binding(
    scheme_name: str,
    collection_name: str | None = None,
    term_form: Literal["label", "notation"] = "label",
) -> VocabularyBinding:
    return VocabularyBinding(scheme_name, collection_name, "", None, term_form)


class TestReleaseFiles:
    def test_release_has_the_given_version_and_the_bare_doi(self) -> None:
        files = ReleaseFiles(RELEASES / "9999.1", "9999.1")

        assert files.release == VocabularyRelease("9999.1", "10.0000/test.1")

    def test_schemes_that_disagree_on_the_doi_are_an_error(self) -> None:
        files = ReleaseFiles(RELEASES / "disagreeing", "9999.1")

        with pytest.raises(ValueError, match="DOI"):
            assert files.release

    def test_resolving_a_binding_fills_in_the_scheme_and_collection_uris(self) -> None:
        files = ReleaseFiles(RELEASES / "9999.1", "9999.1")

        resolved = files.resolve(binding("colours", "warm", "notation"))

        assert resolved == VocabularyBinding(
            "colours", "warm", COLOURS, f"{COLOURS}/warm", "notation"
        )

    def test_resolving_a_binding_without_a_collection_leaves_it_empty(self) -> None:
        files = ReleaseFiles(RELEASES / "9999.1", "9999.1")

        resolved = files.resolve(binding("colours"))

        assert (resolved.scheme, resolved.collection) == (COLOURS, None)

    def test_a_scheme_gives_every_one_of_its_concepts(self) -> None:
        files = ReleaseFiles(RELEASES / "9999.1", "9999.1")

        values = files.allowed_values(binding("colours"))

        assert {value.uri for value in values} == {
            f"{COLOURS}/red",
            f"{COLOURS}/orange",
            f"{COLOURS}/blue",
            f"{COLOURS}/green",
        }

    def test_a_collection_gives_only_its_members(self) -> None:
        files = ReleaseFiles(RELEASES / "9999.1", "9999.1")

        values = files.allowed_values(binding("colours", "warm"))

        assert {value.uri for value in values} == {
            f"{COLOURS}/red",
            f"{COLOURS}/orange",
        }

    def test_a_value_carries_its_english_label_uri_and_notation(self) -> None:
        files = ReleaseFiles(RELEASES / "9999.1", "9999.1")

        values = files.allowed_values(binding("colours", "warm"))

        assert AllowedValue("[red]", "red", f"{COLOURS}/red", "rd") in values

    def test_a_concept_without_a_notation_has_none(self) -> None:
        files = ReleaseFiles(RELEASES / "9999.1", "9999.1")

        values = files.allowed_values(binding("colours"))

        blue = next(value for value in values if value.label == "Blue")
        assert blue.notation is None

    def test_notation_form_uses_the_notation_where_the_concept_has_one(self) -> None:
        files = ReleaseFiles(RELEASES / "9999.1", "9999.1")

        values = files.allowed_values(binding("colours", term_form="notation"))

        assert {value.term for value in values} == {"[rd]", "[or]", "[Blue]", "[green]"}

    def test_label_form_ignores_alternative_and_hidden_labels(self) -> None:
        files = ReleaseFiles(RELEASES / "9999.1", "9999.1")

        values = files.allowed_values(binding("colours"))

        assert {value.term for value in values} == {
            "[red]",
            "[Orange]",
            "[Blue]",
            "[green]",
        }

    def test_values_are_sorted_by_term_ignoring_case(self) -> None:
        files = ReleaseFiles(RELEASES / "9999.1", "9999.1")

        values = files.allowed_values(binding("colours"))

        assert [value.term for value in values] == [
            "[Blue]",
            "[green]",
            "[Orange]",
            "[red]",
        ]

    def test_an_unknown_scheme_name_is_named_in_the_error(self) -> None:
        files = ReleaseFiles(RELEASES / "9999.1", "9999.1")

        with pytest.raises(MissingSchemeError, match="fabrics"):
            files.allowed_values(binding("fabrics"))

    def test_an_unknown_collection_name_is_named_in_the_error(self) -> None:
        files = ReleaseFiles(RELEASES / "9999.1", "9999.1")

        with pytest.raises(MissingSchemeError, match="cool"):
            files.allowed_values(binding("colours", "cool"))
