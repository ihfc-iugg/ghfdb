import re
import warnings
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from frictionless import Field, Schema
from openpyxl import Workbook, load_workbook
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

import ghfdb
from ghfdb.template import FIELD_REFERENCE, VOCABULARIES, TemplateError, UploadTemplate

SOURCE = Path(__file__).parent / "sources" / "upload-template.xlsx"


@pytest.fixture
def workbook(schema: Schema) -> Workbook:
    return UploadTemplate(schema).workbook()


class TestWorkbookLayout:
    def test_has_three_sheets_in_order(self, workbook: Workbook) -> None:
        assert workbook.sheetnames == ["readme", "data list", "controlled vocabulary"]

    def test_header_row_is_id_then_every_code_in_schema_order(
        self,
        workbook: Workbook,
        schema: Schema,
    ) -> None:
        sheet = workbook["data list"]

        header = [cell.value for cell in sheet[1]]

        assert header == ["ID", *schema.field_names]

    def test_matches_the_hand_maintained_template(self, workbook: Workbook) -> None:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=".*extension.*")
            source = load_workbook(SOURCE)
        expected = source["data list"]
        actual = workbook["data list"]

        assert workbook.sheetnames == source.sheetnames
        assert actual["A1"].value == expected["A1"].value
        assert [actual.cell(row, 1).value for row in range(2, 9)] == [
            expected.cell(row, 1).value for row in range(2, 9)
        ]
        assert actual.max_row == 8
        assert not any(cell.value is not None for cell in actual[9])


def first_field(schema: Schema, wanted: Callable[[Field], bool]) -> Field:
    return next(field for field in schema.fields if wanted(field))


def column_of(schema: Schema, field: Field) -> int:
    return schema.field_names.index(field.name) + 2


def enum_of(field: Field) -> list[str]:
    return list(field.constraints.get("enum", []))


class TestDescriptionRows:
    def test_each_row_holds_its_attribute_or_the_marker(
        self, workbook: Workbook, schema: Schema
    ) -> None:
        sheet = workbook["data list"]

        for field in schema.fields:
            column = column_of(schema, field)
            custom = field.custom
            assert sheet.cell(2, column).value == (custom["obligation"] or "-")
            assert sheet.cell(3, column).value == (",".join(custom["domain"]) or "-")
            assert sheet.cell(4, column).value == (custom["qualityRelevance"] or "-")
            assert sheet.cell(5, column).value == field.title
            assert sheet.cell(6, column).value == custom["columnName"]
            assert sheet.cell(7, column).value == (custom["unit"] or "-")

    def test_every_description_cell_is_a_string(
        self, workbook: Workbook, schema: Schema
    ) -> None:
        sheet = workbook["data list"]

        values = [
            sheet.cell(row, column).value
            for row in range(2, 9)
            for column in range(2, len(schema.fields) + 2)
        ]

        assert all(isinstance(value, str) for value in values)

    def test_a_field_with_a_minimum_and_maximum_shows_them_as_a_range(
        self, workbook: Workbook, schema: Schema
    ) -> None:
        field = first_field(
            schema,
            lambda f: "minimum" in f.constraints
            and "maximum" in f.constraints
            and not enum_of(f),
        )
        places = field.custom["decimalPlaces"] or 0
        minimum, maximum = field.constraints["minimum"], field.constraints["maximum"]

        shown = workbook["data list"].cell(8, column_of(schema, field)).value

        assert shown == f"{minimum:,.{places}f} – {maximum:,.{places}f}"

    def test_a_whole_number_range_shows_no_decimal_places(
        self, workbook: Workbook, schema: Schema
    ) -> None:
        field = first_field(
            schema,
            lambda f: "minimum" in f.constraints
            and "maximum" in f.constraints
            and f.custom["decimalPlaces"] is None
            and not enum_of(f),
        )
        minimum, maximum = field.constraints["minimum"], field.constraints["maximum"]

        shown = workbook["data list"].cell(8, column_of(schema, field)).value

        assert shown == f"{int(minimum):,} – {int(maximum):,}"

    def test_a_field_with_only_a_value_format_shows_the_format(
        self, workbook: Workbook, schema: Schema
    ) -> None:
        field = first_field(
            schema,
            lambda f: f.custom["valueFormat"] is not None
            and not ("minimum" in f.constraints and "maximum" in f.constraints)
            and not enum_of(f),
        )

        shown = workbook["data list"].cell(8, column_of(schema, field)).value

        assert shown == field.custom["valueFormat"]

    def test_a_field_with_allowed_values_shows_the_marker(
        self, workbook: Workbook, schema: Schema
    ) -> None:
        field = first_field(schema, lambda f: bool(enum_of(f)))

        shown = workbook["data list"].cell(8, column_of(schema, field)).value

        assert shown == "-"

    def test_a_field_with_no_range_shows_the_marker(
        self, workbook: Workbook, schema: Schema
    ) -> None:
        field = first_field(
            schema,
            lambda f: "minimum" not in f.constraints
            and "maximum" not in f.constraints
            and f.custom["valueFormat"] is None
            and not enum_of(f),
        )

        shown = workbook["data list"].cell(8, column_of(schema, field)).value

        assert shown == "-"


class TestChoiceLists:
    def validations(self, workbook: Workbook) -> dict[str, DataValidation]:
        sheet = workbook["data list"]
        found: dict[str, DataValidation] = {}
        for validation in sheet.data_validations.dataValidation:
            for cells in validation.sqref.ranges:
                assert cells.min_col == cells.max_col
                letter = get_column_letter(cells.min_col)
                assert letter not in found
                found[letter] = validation
        return found

    def test_exactly_the_fields_with_allowed_values_have_a_list(
        self, workbook: Workbook, schema: Schema
    ) -> None:
        expected = {
            get_column_letter(column_of(schema, field))
            for field in schema.fields
            if enum_of(field)
        }

        assert set(self.validations(workbook)) == expected

    def test_a_list_runs_from_row_9_to_the_last_row_and_never_rejects(
        self, workbook: Workbook
    ) -> None:
        for letter, validation in self.validations(workbook).items():
            assert validation.type == "list"
            assert str(validation.sqref) == f"{letter}9:{letter}1048576"
            assert validation.showErrorMessage is False
            assert validation.allow_blank is True

    def test_a_list_points_at_the_terms_of_its_field(
        self, workbook: Workbook, schema: Schema
    ) -> None:
        vocabulary = workbook["controlled vocabulary"]
        validations = self.validations(workbook)

        for field in schema.fields:
            if not enum_of(field):
                continue
            letter = get_column_letter(column_of(schema, field))
            formula = validations[letter].formula1
            assert formula is not None
            match = re.fullmatch(
                r"'controlled vocabulary'!\$([A-Z]+)\$(\d+):\$([A-Z]+)\$(\d+)",
                formula,
            )
            assert match is not None
            first, start, last, end = match.groups()
            assert first == last == letter
            terms = [
                vocabulary[f"{letter}{row}"].value
                for row in range(int(start), int(end) + 1)
            ]
            assert terms == enum_of(field)

    def test_the_vocabulary_sheet_names_each_field_above_its_terms(
        self, workbook: Workbook, schema: Schema
    ) -> None:
        vocabulary = workbook["controlled vocabulary"]

        assert vocabulary["A1"].value == "Field code"
        assert vocabulary["A2"].value == "Name"
        for field in schema.fields:
            letter = get_column_letter(column_of(schema, field))
            if enum_of(field):
                assert vocabulary[f"{letter}1"].value == field.name
                assert vocabulary[f"{letter}2"].value == field.title
                assert vocabulary[f"{letter}3"].value == enum_of(field)[0]
            else:
                assert vocabulary[f"{letter}1"].value is None

    def test_a_vocabulary_field_without_allowed_values_raises_naming_it(
        self,
        schema: Schema,
        without_allowed_values: Callable[[Schema, str], Schema],
    ) -> None:
        bound = first_field(schema, lambda f: f.custom["vocabulary"] is not None)
        template = UploadTemplate(without_allowed_values(schema, bound.name))

        with pytest.raises(TemplateError, match=bound.name):
            template.workbook()


class TestReadme:
    def test_states_the_package_version_and_where_the_vocabularies_are(
        self, workbook: Workbook, schema: Schema
    ) -> None:
        sheet = workbook["readme"]

        lines = [str(row[0].value or "") for row in sheet.iter_rows()]

        assert any(ghfdb.__version__ in line for line in lines)
        assert any(VOCABULARIES in line for line in lines)
        assert any(FIELD_REFERENCE in line for line in lines)

    def test_exposes_the_version_it_states(self, schema: Schema) -> None:
        assert UploadTemplate(schema).version == ghfdb.__version__


class TestWrite:
    def test_writes_the_template_to_a_new_path(
        self, tmp_path: Path, schema: Schema
    ) -> None:
        path = tmp_path / "template.xlsx"

        UploadTemplate(schema).write(path)

        written = load_workbook(path)
        assert written.sheetnames == ["readme", "data list", "controlled vocabulary"]
        assert written["data list"]["B1"].value == schema.field_names[0]

    def test_refuses_an_existing_file_naming_the_path_and_leaves_it_untouched(
        self, tmp_path: Path, schema: Schema
    ) -> None:
        path = tmp_path / "template.xlsx"
        path.write_bytes(b"not a template")

        with pytest.raises(FileExistsError, match="replace=True") as raised:
            UploadTemplate(schema).write(path)

        assert str(path) in str(raised.value)
        assert path.read_bytes() == b"not a template"

    def test_replaces_an_existing_file_when_asked(
        self, tmp_path: Path, schema: Schema
    ) -> None:
        path = tmp_path / "template.xlsx"
        path.write_bytes(b"not a template")

        UploadTemplate(schema).write(path, replace=True)

        assert load_workbook(path).sheetnames == [
            "readme",
            "data list",
            "controlled vocabulary",
        ]

    def test_does_not_create_a_file_when_the_workbook_cannot_be_built(
        self,
        tmp_path: Path,
        schema: Schema,
        without_allowed_values: Callable[[Schema, str], Schema],
    ) -> None:
        bound = first_field(schema, lambda f: f.custom["vocabulary"] is not None)
        template = UploadTemplate(without_allowed_values(schema, bound.name))
        path = tmp_path / "template.xlsx"

        with pytest.raises(TemplateError):
            template.write(path)

        assert not path.exists()


class TestIdenticalContent:
    def test_two_generations_have_identical_content(
        self,
        tmp_path: Path,
        schema: Schema,
        workbook_content: Callable[[Path], dict[str, Any]],
    ) -> None:
        first, second = tmp_path / "first.xlsx", tmp_path / "second.xlsx"

        UploadTemplate(schema).write(first)
        UploadTemplate(schema).write(second)

        assert workbook_content(first) == workbook_content(second)

    def test_the_content_holds_the_sheets_cells_and_validations(
        self,
        tmp_path: Path,
        schema: Schema,
        workbook_content: Callable[[Path], dict[str, Any]],
    ) -> None:
        path = tmp_path / "template.xlsx"
        UploadTemplate(schema).write(path)

        content = workbook_content(path)

        assert list(content) == ["readme", "data list", "controlled vocabulary"]
        assert content["data list"]["cells"]["A1"] == "ID"
        choice_fields = [f for f in schema.fields if enum_of(f)]
        assert len(content["data list"]["validations"]) == len(choice_fields)
