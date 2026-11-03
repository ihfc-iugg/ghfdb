import warnings
from collections.abc import Callable
from pathlib import Path

import pytest
from openpyxl import Workbook, load_workbook

from ghfdb.fields import Field, FieldSchema
from ghfdb.template import UploadTemplate

SOURCE = Path(__file__).parent / "sources" / "upload-template.xlsx"


@pytest.fixture(scope="module")
def schema() -> FieldSchema:
    return FieldSchema.load()


@pytest.fixture
def workbook(schema: FieldSchema) -> Workbook:
    return UploadTemplate(schema).workbook()


class TestWorkbookLayout:
    def test_has_three_sheets_in_order(self, workbook: Workbook) -> None:
        assert workbook.sheetnames == ["readme", "data list", "controlled vocabulary"]

    def test_header_row_is_id_then_every_code_in_schema_order(
        self,
        workbook: Workbook,
        schema: FieldSchema,
    ) -> None:
        sheet = workbook["data list"]

        header = [cell.value for cell in sheet[1]]

        assert header == ["ID", *(field.code for field in schema)]

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


def first_field(schema: FieldSchema, wanted: Callable[[Field], bool]) -> Field:
    return next(field for field in schema if wanted(field))


def column_of(schema: FieldSchema, field: Field) -> int:
    return list(schema).index(field) + 2


class TestDescriptionRows:
    def test_each_row_holds_its_attribute_or_the_marker(
        self, workbook: Workbook, schema: FieldSchema
    ) -> None:
        sheet = workbook["data list"]

        for field in schema:
            column = column_of(schema, field)
            assert sheet.cell(2, column).value == (field.obligation or "-")
            assert sheet.cell(3, column).value == (",".join(field.domain) or "-")
            assert sheet.cell(4, column).value == (field.quality_relevance or "-")
            assert sheet.cell(5, column).value == field.name
            assert sheet.cell(6, column).value == field.column_name
            assert sheet.cell(7, column).value == (field.unit or "-")

    def test_every_description_cell_is_a_string(
        self, workbook: Workbook, schema: FieldSchema
    ) -> None:
        sheet = workbook["data list"]

        values = [
            sheet.cell(row, column).value
            for row in range(2, 9)
            for column in range(2, len(schema) + 2)
        ]

        assert all(isinstance(value, str) for value in values)

    def test_a_field_with_a_minimum_and_maximum_shows_them_as_a_range(
        self, workbook: Workbook, schema: FieldSchema
    ) -> None:
        field = first_field(
            schema,
            lambda f: f.minimum is not None
            and f.maximum is not None
            and not f.allowed_values,
        )
        places = field.decimal_places or 0
        assert field.minimum is not None and field.maximum is not None

        shown = workbook["data list"].cell(8, column_of(schema, field)).value

        assert shown == (f"{field.minimum:,.{places}f} – {field.maximum:,.{places}f}")

    def test_a_field_with_only_a_value_format_shows_the_format(
        self, workbook: Workbook, schema: FieldSchema
    ) -> None:
        field = first_field(
            schema,
            lambda f: f.value_format is not None
            and (f.minimum is None or f.maximum is None)
            and not f.allowed_values,
        )

        shown = workbook["data list"].cell(8, column_of(schema, field)).value

        assert shown == field.value_format

    def test_a_field_with_allowed_values_shows_the_marker(
        self, workbook: Workbook, schema: FieldSchema
    ) -> None:
        field = first_field(schema, lambda f: bool(f.allowed_values))

        shown = workbook["data list"].cell(8, column_of(schema, field)).value

        assert shown == "-"

    def test_a_field_with_no_range_shows_the_marker(
        self, workbook: Workbook, schema: FieldSchema
    ) -> None:
        field = first_field(
            schema,
            lambda f: f.minimum is None
            and f.maximum is None
            and f.value_format is None
            and not f.allowed_values,
        )

        shown = workbook["data list"].cell(8, column_of(schema, field)).value

        assert shown == "-"
