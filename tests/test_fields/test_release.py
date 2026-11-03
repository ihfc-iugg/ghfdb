import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Literal

import pytest

from ghfdb.fields.release import (
    FieldChange,
    MissingSchemeError,
    ReleaseFiles,
    ReleaseMove,
    main,
)
from ghfdb.fields.schema import (
    AllowedValue,
    FieldSchema,
    VocabularyBinding,
    VocabularyRelease,
)

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


SHAPES = "https://example.test/vocabularies/shapes"


def two_field_schema() -> dict[str, Any]:
    def field(name: str, scheme_name: str) -> dict[str, Any]:
        return {
            "name": name,
            "title": name,
            "constraints": {"enum": []},
            "vocabulary": {
                "schemeName": scheme_name,
                "collectionName": None,
                "scheme": "",
                "collection": None,
                "termForm": "label",
            },
            "allowedValues": [],
        }

    return {
        "vocabularyRelease": {"version": "0000.0", "doi": "10.0000/old.0"},
        "fields": [field("X1", "colours"), field("X2", "shapes"), {"name": "X3"}],
    }


def moved_to_a(tmp_path: Path) -> Path:
    path = tmp_path / "schema.json"
    write(path, two_field_schema())
    ReleaseMove(path, ReleaseFiles(RELEASES / "9999.1", "9999.1")).apply()
    return path


def term_set(values: tuple[AllowedValue, ...]) -> set[str]:
    return {value.term for value in values}


class TestReleaseMoveChanges:
    def test_a_field_lists_the_concepts_added_removed_and_relabelled(
        self, tmp_path: Path
    ) -> None:
        path = moved_to_a(tmp_path)
        move = ReleaseMove(path, ReleaseFiles(RELEASES / "9999.2", "9999.2"))

        change = move.changes()[0]

        assert change.code == "X1"
        assert term_set(change.added) == {"[purple]"}
        assert term_set(change.removed) == {"[green]"}
        assert [(old.term, new.term) for old, new in change.relabelled] == [
            ("[Blue]", "[Indigo]")
        ]

    def test_a_field_whose_concepts_are_the_same_has_an_empty_change(
        self, tmp_path: Path
    ) -> None:
        path = moved_to_a(tmp_path)
        move = ReleaseMove(path, ReleaseFiles(RELEASES / "9999.2", "9999.2"))

        assert move.changes()[1] == FieldChange("X2", (), (), ())

    def test_there_is_one_change_per_vocabulary_field_in_file_order(
        self, tmp_path: Path
    ) -> None:
        path = moved_to_a(tmp_path)
        move = ReleaseMove(path, ReleaseFiles(RELEASES / "9999.2", "9999.2"))

        assert [change.code for change in move.changes()] == ["X1", "X2"]

    def test_reporting_changes_leaves_the_file_untouched(self, tmp_path: Path) -> None:
        path = moved_to_a(tmp_path)
        before = path.read_bytes()

        ReleaseMove(path, ReleaseFiles(RELEASES / "9999.2", "9999.2")).changes()

        assert path.read_bytes() == before

    def test_applying_returns_the_same_changes(self, tmp_path: Path) -> None:
        path = moved_to_a(tmp_path)
        move = ReleaseMove(path, ReleaseFiles(RELEASES / "9999.2", "9999.2"))
        expected = move.changes()

        assert move.apply() == expected

    def test_a_field_that_has_just_been_moved_has_no_changes(
        self, tmp_path: Path
    ) -> None:
        path = moved_to_a(tmp_path)
        move = ReleaseMove(path, ReleaseFiles(RELEASES / "9999.1", "9999.1"))

        assert all(not change.added for change in move.changes())


class TestReleaseMoveAtomic:
    def test_a_missing_scheme_names_the_field_and_the_scheme(
        self, tmp_path: Path
    ) -> None:
        path = moved_to_a(tmp_path)
        move = ReleaseMove(path, ReleaseFiles(RELEASES / "9999.3", "9999.3"))

        with pytest.raises(MissingSchemeError, match=r"X2.*shapes"):
            move.apply()

    def test_a_missing_scheme_leaves_the_file_byte_for_byte_unchanged(
        self, tmp_path: Path
    ) -> None:
        path = moved_to_a(tmp_path)
        before = path.read_bytes()
        move = ReleaseMove(path, ReleaseFiles(RELEASES / "9999.3", "9999.3"))

        with pytest.raises(MissingSchemeError):
            move.apply()

        assert path.read_bytes() == before

    def test_a_missing_scheme_is_also_reported_by_changes(self, tmp_path: Path) -> None:
        path = moved_to_a(tmp_path)
        move = ReleaseMove(path, ReleaseFiles(RELEASES / "9999.3", "9999.3"))

        with pytest.raises(MissingSchemeError, match="X2"):
            move.changes()

    def test_a_complete_release_changes_only_the_generated_facts(
        self, tmp_path: Path
    ) -> None:
        path = moved_to_a(tmp_path)
        before = json.loads(path.read_text())

        ReleaseMove(path, ReleaseFiles(RELEASES / "9999.2", "9999.2")).apply()

        after = json.loads(path.read_text())
        for old, new in zip(before["fields"], after["fields"], strict=True):
            for key in set(old) | set(new):
                if key not in ("vocabulary", "allowedValues", "constraints"):
                    assert old[key] == new[key]
        assert after["vocabularyRelease"] == {
            "version": "9999.2",
            "doi": "10.0000/test.2",
        }


CHANGELOG = """# Changelog

## [Unreleased]

### Added

- Something.

## [1.0.0] - 2026-01-01

### Changed

- Older.
"""


def run_main(
    tmp_path: Path, version: str, changelog_text: str = CHANGELOG
) -> tuple[int, Path, Path]:
    schema = moved_to_a(tmp_path)
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(changelog_text)
    code = main(
        [
            version,
            str(RELEASES / version),
            "--schema",
            str(schema),
            "--changelog",
            str(changelog),
        ]
    )
    return code, schema, changelog


class TestMain:
    def test_it_prints_one_line_per_vocabulary_field(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code, _, _ = run_main(tmp_path, "9999.2")

        lines = capsys.readouterr().out.splitlines()
        assert code == 0
        assert [line.split(":")[0] for line in lines] == ["X1", "X2"]
        assert lines[1] == "X2: unchanged"
        assert all(term in lines[0] for term in ("[purple]", "[green]", "[Indigo]"))

    def test_it_writes_the_new_release_into_the_schema(self, tmp_path: Path) -> None:
        _, schema, _ = run_main(tmp_path, "9999.2")

        assert json.loads(schema.read_text())["vocabularyRelease"]["version"] == (
            "9999.2"
        )

    def test_it_adds_a_line_naming_both_releases_under_changed(
        self, tmp_path: Path
    ) -> None:
        _, _, changelog = run_main(tmp_path, "9999.2")

        text = changelog.read_text()
        unreleased = text.split("## [1.0.0]")[0]
        added = unreleased.split("### Changed")[1]
        assert "9999.1" in added
        assert "10.0000/test.1" in added
        assert "9999.2" in added
        assert "10.0000/test.2" in added
        assert text.endswith("- Older.\n")

    def test_it_creates_the_changed_heading_when_it_is_absent(
        self, tmp_path: Path
    ) -> None:
        bare = "# Changelog\n\n## [Unreleased]\n\n### Added\n\n- Something.\n"

        _, _, changelog = run_main(tmp_path, "9999.2", bare)

        lines = changelog.read_text().splitlines()
        heading = lines.index("### Changed")
        assert lines[heading - 2 : heading] == ["- Something.", ""]
        assert "9999.2" in lines[heading + 2]

    def test_a_missing_scheme_exits_one_and_changes_neither_file(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        schema = moved_to_a(tmp_path)
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(CHANGELOG)
        before = (schema.read_bytes(), changelog.read_bytes())

        code = main(
            [
                "9999.3",
                str(RELEASES / "9999.3"),
                "--schema",
                str(schema),
                "--changelog",
                str(changelog),
            ]
        )

        assert code == 1
        assert (schema.read_bytes(), changelog.read_bytes()) == before
        assert "X2" in capsys.readouterr().err


SHIPPED = FieldSchema.load()
VOCABULARIES = Path(__file__).parents[2] / "vocabularies"


def differences(schema_path: Path) -> dict[str, list[str]]:
    """The facts of each field that its stated release does not give."""
    schema = FieldSchema.load(schema_path)
    files = ReleaseFiles(VOCABULARIES / schema.release.version, schema.release.version)
    enums = {
        entry["name"]: entry.get("constraints", {}).get("enum")
        for entry in json.loads(schema_path.read_text())["fields"]
    }
    found: dict[str, list[str]] = {}
    if files.release != schema.release:
        found["release"] = [f"the files give {files.release}, not {schema.release}"]
    for field in schema:
        wrong = []
        values = field.allowed_values
        if field.vocabulary is not None:
            resolved = files.resolve(field.vocabulary)
            values = files.allowed_values(field.vocabulary)
            if resolved != field.vocabulary:
                wrong.append("scheme or collection")
            if values != field.allowed_values:
                wrong.append("allowed values")
        if values and enums[field.code] != [value.term for value in values]:
            wrong.append("constraints.enum")
        if wrong:
            found[field.code] = wrong
    return found


class TestShippedSchemaDrift:
    def test_every_vocabulary_field_matches_its_stated_release(self) -> None:
        assert differences(SHIPPED.path) == {}

    def test_a_hand_edited_allowed_term_is_reported_with_its_field(
        self, tmp_path: Path
    ) -> None:
        data = json.loads(SHIPPED.path.read_text())
        field = next(f for f in data["fields"] if f.get("vocabulary"))
        field["allowedValues"][0]["term"] = "[edited by hand]"
        path = tmp_path / "schema.json"
        write(path, data)

        assert list(differences(path)) == [field["name"]]

    def test_an_edited_enum_is_reported_with_its_field(self, tmp_path: Path) -> None:
        data = json.loads(SHIPPED.path.read_text())
        field = next(f for f in data["fields"] if f["name"] == "P9")
        field["constraints"]["enum"].reverse()
        path = tmp_path / "schema.json"
        write(path, data)

        assert differences(path) == {"P9": ["constraints.enum"]}

    def test_a_stated_doi_that_the_release_does_not_give_is_reported(
        self, tmp_path: Path
    ) -> None:
        data = json.loads(SHIPPED.path.read_text())
        data["vocabularyRelease"]["doi"] = "10.0000/not-the-release"
        path = tmp_path / "schema.json"
        write(path, data)

        assert list(differences(path)) == ["release"]
