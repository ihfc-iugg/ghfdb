from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from extensions.upload_template import (
    HAND_MAINTAINED,
    PREVIOUS_LABELS,
    TemplateChanges,
    read_hand_maintained,
    replace_markers,
    template_name,
    write_template,
)
from openpyxl import Workbook

import ghfdb
from ghfdb.fields import FieldSchema
from ghfdb.template import ROW_LABELS, TemplateError, UploadTemplate


@pytest.fixture(scope="module")
def schema() -> FieldSchema:
    return FieldSchema.load()


class TestTemplateName:
    def test_names_the_file_for_the_package_version(self) -> None:
        assert template_name(ghfdb.__version__).endswith(f"{ghfdb.__version__}.xlsx")


class TestWriteTemplate:
    def test_writes_the_versioned_file_beside_the_page(self, tmp_path: Path) -> None:
        path = write_template(UploadTemplate(), tmp_path)

        assert path == tmp_path / "upload-template" / template_name(ghfdb.__version__)
        assert path.is_file()

    def test_content_equals_what_a_developer_writes(
        self,
        tmp_path: Path,
        workbook_content: Callable[[Path], dict[str, Any]],
    ) -> None:
        published = write_template(UploadTemplate(), tmp_path)
        developer = tmp_path / "developer.xlsx"
        UploadTemplate().write(developer)

        assert workbook_content(published) == workbook_content(developer)

    def test_replaces_the_file_of_an_earlier_build(self, tmp_path: Path) -> None:
        write_template(UploadTemplate(), tmp_path)

        path = write_template(UploadTemplate(), tmp_path)

        assert path.is_file()

    def test_a_generation_error_propagates(
        self, tmp_path: Path, schema: FieldSchema
    ) -> None:
        bound = next(field for field in schema if field.vocabulary is not None)
        emptied = replace(bound, allowed_values=())
        fields = tuple(emptied if f is bound else f for f in schema)
        template = UploadTemplate(FieldSchema(schema.path, schema.release, fields))

        with pytest.raises(TemplateError, match=bound.code):
            write_template(template, tmp_path)


def empty_changes() -> TemplateChanges:
    both = {"X1": described("one")}
    return TemplateChanges(build_workbook(both), build_workbook(both))


class TestReplaceMarkers:
    def test_the_download_marker_becomes_a_download_link_to_the_versioned_file(
        self,
    ) -> None:
        name = template_name(ghfdb.__version__)

        text = replace_markers(
            "Before\n\n{upload-template-download}\n\nAfter", name, empty_changes()
        )

        assert f"{{download}}`{name} <{name}>`" in text
        assert "{upload-template-download}" not in text

    def test_a_page_without_markers_is_unchanged(self) -> None:
        text = "# A page\n\nMentions {upload-template-download} inline only.\n"

        assert replace_markers(text, "any.xlsx", empty_changes()) == text


def build_workbook(
    descriptions: dict[str, list[Any]],
    lists: dict[str, list[str]] | None = None,
    previous: bool = False,
) -> Workbook:
    """Build a small workbook laid out like the template.

    The previous layout labels each vocabulary column with the field's name, as the
    hand-maintained template does; the generated layout labels it with the code.
    """
    workbook = Workbook()
    data_list = workbook.active
    assert data_list is not None
    data_list.title = "data list"
    vocabulary = workbook.create_sheet("controlled vocabulary")
    data_list["A1"] = "ID"
    for row, label in enumerate(ROW_LABELS, start=2):
        data_list.cell(row, 1, label)
    vocabulary["A1"] = "Field code"
    for index, (code, rows) in enumerate(descriptions.items(), start=2):
        data_list.cell(1, index, code)
        for row, value in enumerate(rows, start=2):
            data_list.cell(row, index, value)
    for index, (code, terms) in enumerate((lists or {}).items(), start=2):
        label = descriptions[code][3] if previous else code
        vocabulary.cell(1, index, label)
        for row, term in enumerate(terms, start=3):
            vocabulary.cell(row, index, f"[{term}]")
    return workbook


def described(name: str, **changes: Any) -> list[Any]:
    rows: list[Any] = ["M", "B", "Q", name, name, "m", "-"]
    for position, value in changes.items():
        rows[int(position.removeprefix("row")) - 2] = value
    return rows


def compare(
    before: dict[str, list[Any]],
    after: dict[str, list[Any]],
    before_lists: dict[str, list[str]] | None = None,
    after_lists: dict[str, list[str]] | None = None,
) -> TemplateChanges:
    return TemplateChanges(
        build_workbook(before, before_lists, previous=True),
        build_workbook(after, after_lists),
    )


class TestTemplateChangesColumns:
    def test_reports_added_and_removed_codes(self) -> None:
        changes = compare(
            {"X1": described("one"), "X2": described("two")},
            {"X1": described("one"), "X3": described("three")},
        )

        assert changes.columns() == (["X3"], ["X2"], False)

    def test_reports_a_change_of_order_among_the_common_codes(self) -> None:
        changes = compare(
            {"X1": described("one"), "X2": described("two")},
            {"X2": described("two"), "X1": described("one")},
        )

        assert changes.columns() == ([], [], True)

    def test_a_removed_code_alone_is_not_a_reorder(self) -> None:
        changes = compare(
            {"X1": described("one"), "X2": described("two"), "X3": described("3")},
            {"X1": described("one"), "X3": described("3")},
        )

        assert changes.columns() == ([], ["X2"], False)


class TestTemplateChangesDescriptionRows:
    def test_reports_each_changed_cell_with_both_values(self) -> None:
        changes = compare(
            {"X1": described("one", row6="old")},
            {"X1": described("one", row6="new")},
        )

        assert changes.description_rows() == [("X1", "Short Name", "old", "new")]

    def test_ignores_differences_in_whitespace_only(self) -> None:
        changes = compare(
            {"X1": described("one  thing\xa0", row8=None)},
            {"X1": described(" one thing", row8="")},
        )

        assert changes.description_rows() == []

    def test_compares_numbers_as_text(self) -> None:
        changes = compare(
            {"X1": described("one", row8="5")},
            {"X1": described("one", row8=5)},
        )

        assert changes.description_rows() == []

    def test_skips_codes_in_only_one_workbook(self) -> None:
        changes = compare(
            {"X1": described("one")},
            {"X2": described("two", row2="O")},
        )

        assert changes.description_rows() == []


class TestTemplateChangesChoiceLists:
    def test_reports_terms_added_and_removed_in_a_list_both_have(self) -> None:
        changes = compare(
            {"X1": described("one")},
            {"X1": described("one")},
            {"X1": ["kept", "dropped"]},
            {"X1": ["kept", "new"]},
        )

        assert changes.choice_lists() == ([("X1", ["[new]"], ["[dropped]"])], [], [])

    def test_reports_no_change_for_the_same_terms(self) -> None:
        changes = compare(
            {"X1": described("one")},
            {"X1": described("one")},
            {"X1": ["kept"]},
            {"X1": ["kept"]},
        )

        assert changes.choice_lists() == ([], [], [])

    def test_reports_a_list_gained_and_a_list_lost(self) -> None:
        both = {"X1": described("one"), "X2": described("two")}
        changes = compare(both, both, {"X1": ["a"]}, {"X2": ["b"]})

        assert changes.choice_lists() == ([], ["X2"], ["X1"])

    def test_a_vocabulary_column_without_brackets_is_not_a_list(self) -> None:
        workbook = build_workbook({"X1": described("one")}, {"X1": ["a"]}, True)
        workbook["controlled vocabulary"]["B3"] = "= Multiple choices ="

        changes = TemplateChanges(
            workbook, build_workbook({"X1": described("one")}, {"X1": ["b"]})
        )

        assert changes.choice_lists() == ([], ["X1"], [])

    def test_maps_the_one_label_that_is_not_a_name(self) -> None:
        label = next(iter(PREVIOUS_LABELS))
        code = PREVIOUS_LABELS[label]
        workbook = build_workbook({code: described("other")}, {code: ["a"]}, True)
        workbook["controlled vocabulary"]["B1"] = label

        changes = TemplateChanges(
            workbook, build_workbook({code: described("other")}, {code: ["a"]})
        )

        assert changes.choice_lists() == ([], [], [])

    def test_a_column_with_terms_that_matches_no_field_raises_naming_it(self) -> None:
        workbook = build_workbook({"X1": described("one")}, {"X1": ["a"]}, True)
        workbook["controlled vocabulary"]["B1"] = "Unknown label"

        changes = TemplateChanges(workbook, build_workbook({"X1": described("one")}))

        with pytest.raises(ValueError, match="Unknown label"):
            changes.choice_lists()


class TestTemplateChangesMarkdown:
    def test_has_a_heading_for_each_kind_of_change(self) -> None:
        changes = compare({"X1": described("one")}, {"X1": described("one")})

        markdown = changes.markdown()

        assert markdown.count("\n### ") + markdown.startswith("### ") == 3

    def test_says_none_under_a_heading_with_no_changes(self) -> None:
        changes = compare({"X1": described("one")}, {"X1": described("one")})

        assert changes.markdown().count("None.") == 3

    def test_tabulates_the_changes_and_escapes_the_cells(self) -> None:
        changes = compare(
            {"X1": described("one", row6="a|b")},
            {"X1": described("one", row6="c_d"), "X2": described("two")},
            {"X1": ["gone"]},
            {"X1": ["fresh"]},
        )

        markdown = changes.markdown()

        assert "None." not in markdown
        assert "X2" in markdown
        assert r"a\|b" in markdown
        assert r"c\_d" in markdown
        assert "gone" in markdown
        assert "fresh" in markdown


@pytest.fixture(scope="module")
def changes() -> TemplateChanges:
    return TemplateChanges(read_hand_maintained(), UploadTemplate().workbook())


class TestTemplateChangesOnTheRealPair:
    def test_finds_the_short_name_of_c46_changed(
        self, changes: TemplateChanges, schema: FieldSchema
    ) -> None:
        sheet = changes.previous["data list"]
        column = next(cell.column for cell in sheet[1] if cell.value == "C46")
        before = str(sheet.cell(6, column).value).strip()

        found = [
            row
            for row in changes.description_rows()
            if row[:2] == ("C46", "Short Name")
        ]

        assert found == [("C46", "Short Name", before, schema["C46"].column_name)]

    def test_finds_the_choice_list_of_c20_lost(
        self, changes: TemplateChanges, schema: FieldSchema
    ) -> None:
        _, gained, lost = changes.choice_lists()

        assert not schema["C20"].allowed_values
        assert "C20" in lost
        assert "C20" not in gained

    def test_never_writes_the_hand_maintained_workbook(self) -> None:
        before = HAND_MAINTAINED.stat().st_mtime_ns

        TemplateChanges(read_hand_maintained(), UploadTemplate().workbook()).markdown()

        assert HAND_MAINTAINED.stat().st_mtime_ns == before
