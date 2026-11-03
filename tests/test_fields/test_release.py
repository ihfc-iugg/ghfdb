import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Literal

import pytest

from ghfdb.fields.release import MissingSchemeError, ReleaseFiles, ReleaseMove
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


def stale_schema() -> dict[str, Any]:
    return {
        "missingValues": [""],
        "vocabularyRelease": {"version": "0000.0", "doi": "10.0000/old.0"},
        "fields": [
            {
                "name": "X1",
                "title": "Température",
                "constraints": {"maxLength": 255, "enum": ["[Stale]"]},
                "vocabulary": {
                    "schemeName": "colours",
                    "collectionName": "warm",
                    "scheme": "https://old.test/colours",
                    "collection": "https://old.test/colours/warm",
                    "termForm": "notation",
                },
                "allowedValues": [
                    {
                        "term": "[Stale]",
                        "uri": "u:s",
                        "label": "Stale",
                        "notation": None,
                    }
                ],
                "sources": {"vocabulary": "vocabulary-release"},
            },
            {
                "name": "X2",
                "title": "Fixed",
                "constraints": {"enum": ["[Yes]"]},
                "vocabulary": None,
                "allowedValues": [
                    {"term": "[Yes]", "uri": None, "label": "Yes", "notation": None}
                ],
            },
            {"name": "X3", "title": "Plain", "constraints": {"minimum": 0}},
        ],
    }


def write(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


class TestReleaseMove:
    def test_a_vocabulary_field_takes_the_release_generated_facts(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "schema.json"
        write(path, stale_schema())
        files = ReleaseFiles(RELEASES / "9999.1", "9999.1")

        ReleaseMove(path, files).apply()

        field = json.loads(path.read_text())["fields"][0]
        assert field["vocabulary"] == {
            "schemeName": "colours",
            "collectionName": "warm",
            "scheme": COLOURS,
            "collection": f"{COLOURS}/warm",
            "termForm": "notation",
        }
        assert [value["term"] for value in field["allowedValues"]] == ["[or]", "[rd]"]
        assert field["constraints"]["enum"] == ["[or]", "[rd]"]

    def test_an_allowed_value_is_written_with_all_four_properties(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "schema.json"
        write(path, stale_schema())
        files = ReleaseFiles(RELEASES / "9999.1", "9999.1")

        ReleaseMove(path, files).apply()

        written = json.loads(path.read_text())["fields"][0]["allowedValues"][1]
        assert written == {
            "term": "[rd]",
            "uri": f"{COLOURS}/red",
            "label": "red",
            "notation": "rd",
        }

    def test_the_schema_takes_the_release_version_and_doi(self, tmp_path: Path) -> None:
        path = tmp_path / "schema.json"
        write(path, stale_schema())
        files = ReleaseFiles(RELEASES / "9999.1", "9999.1")

        ReleaseMove(path, files).apply()

        assert json.loads(path.read_text())["vocabularyRelease"] == {
            "version": "9999.1",
            "doi": "10.0000/test.1",
        }

    def test_every_other_property_of_every_field_is_unchanged(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "schema.json"
        before = stale_schema()
        write(path, before)
        files = ReleaseFiles(RELEASES / "9999.1", "9999.1")

        ReleaseMove(path, files).apply()

        after = json.loads(path.read_text())
        expected = deepcopy(before)
        expected["vocabularyRelease"] = after["vocabularyRelease"]
        for key in ("vocabulary", "allowedValues"):
            expected["fields"][0][key] = after["fields"][0][key]
        expected["fields"][0]["constraints"]["enum"] = after["fields"][0][
            "constraints"
        ]["enum"]
        assert after == expected
        assert list(after["fields"][0]["constraints"]) == ["maxLength", "enum"]

    def test_the_file_is_written_in_the_single_serializer_form(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "schema.json"
        write(path, stale_schema())
        files = ReleaseFiles(RELEASES / "9999.1", "9999.1")

        ReleaseMove(path, files).apply()

        text = path.read_text()
        assert text == json.dumps(json.loads(text), indent=2, ensure_ascii=False) + "\n"
        assert "Température" in text
