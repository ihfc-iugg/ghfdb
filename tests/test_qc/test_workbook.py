from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest
from frictionless import Schema
from openpyxl import Workbook, load_workbook

from ghfdb.qc.workbook import CheckError, UploadWorkbook
from ghfdb.template import FIRST_DATA_ROW, ROW_LABELS

Filler = Callable[[Sequence[Mapping[str, Any]]], Path]
SOURCE = Path(__file__).parent.parent / "sources" / "upload-template.xlsx"


def edit(path: Path, change: Callable[[Any], None]) -> Path:
    """Apply a change to the ``data list`` sheet of a workbook, in place."""
    workbook = load_workbook(path)
    change(workbook["data list"])
    workbook.save(path)
    return path


class TestUploadWorkbookLayout:
    def test_finds_the_header_and_data_of_a_generated_template(
        self, schema: Schema, filled_workbook: Filler, valid_child: dict[str, Any]
    ) -> None:
        path = filled_workbook([valid_child])

        workbook = UploadWorkbook(path, schema)

        assert workbook.header_row == 1
        assert workbook.first_data_row == FIRST_DATA_ROW
        assert set(workbook.columns) == {field.name for field in schema.fields}
        assert workbook.unknown_columns == []
        assert workbook.duplicate_columns == []

    def test_finds_the_header_and_data_of_the_hand_maintained_template(
        self, schema: Schema
    ) -> None:
        workbook = UploadWorkbook(SOURCE, schema)

        assert workbook.header_row == 1
        assert workbook.first_data_row == FIRST_DATA_ROW
        assert set(workbook.columns) == {field.name for field in schema.fields}
        assert workbook.unknown_columns == []
        assert workbook.duplicate_columns == []

    def test_does_not_change_the_workbook_it_reads(
        self, schema: Schema, filled_workbook: Filler, valid_child: dict[str, Any]
    ) -> None:
        path = filled_workbook([valid_child])
        before = path.read_bytes()

        UploadWorkbook(path, schema)

        assert path.read_bytes() == before

    def test_starts_data_after_more_description_rows(
        self, schema: Schema, filled_workbook: Filler, valid_child: dict[str, Any]
    ) -> None:
        path = edit(
            filled_workbook([valid_child]),
            lambda sheet: sheet.insert_rows(3, 2),
        )
        edit(path, lambda sheet: sheet.cell(3, 1, ROW_LABELS[0].upper()))
        edit(path, lambda sheet: sheet.cell(4, 1, f"  {ROW_LABELS[-1]} "))

        workbook = UploadWorkbook(path, schema)

        assert workbook.first_data_row == FIRST_DATA_ROW + 2

    def test_starts_data_after_fewer_description_rows(
        self, schema: Schema, filled_workbook: Filler, valid_child: dict[str, Any]
    ) -> None:
        path = edit(
            filled_workbook([valid_child]),
            lambda sheet: sheet.delete_rows(2, len(ROW_LABELS)),
        )

        workbook = UploadWorkbook(path, schema)

        assert workbook.first_data_row == 2

    def test_reads_a_row_with_another_label_as_a_child(
        self, schema: Schema, filled_workbook: Filler, valid_child: dict[str, Any]
    ) -> None:
        path = edit(
            filled_workbook([valid_child]),
            lambda sheet: sheet.cell(FIRST_DATA_ROW - 1, 1, "Remarks"),
        )

        workbook = UploadWorkbook(path, schema)

        assert workbook.first_data_row == FIRST_DATA_ROW - 1

    def test_finds_a_header_that_is_not_in_the_first_row(
        self, schema: Schema, filled_workbook: Filler, valid_child: dict[str, Any]
    ) -> None:
        path = edit(
            filled_workbook([valid_child]),
            lambda sheet: sheet.insert_rows(1, 2),
        )

        workbook = UploadWorkbook(path, schema)

        assert workbook.header_row == 3
        assert workbook.first_data_row == FIRST_DATA_ROW + 2

    def test_finds_a_header_in_a_sheet_that_starts_at_b3(
        self, schema: Schema, filled_workbook: Filler, valid_child: dict[str, Any]
    ) -> None:
        def move(sheet: Any) -> None:
            sheet.move_range(sheet.dimensions, rows=2, cols=1)

        path = edit(filled_workbook([valid_child]), move)

        workbook = UploadWorkbook(path, schema)

        assert workbook.header_row == 3
        assert workbook.first_data_row == FIRST_DATA_ROW + 2
        assert set(workbook.columns) == {field.name for field in schema.fields}
        assert workbook.unknown_columns == []

    def test_recognises_a_published_column_name(
        self, schema: Schema, filled_workbook: Filler, valid_child: dict[str, Any]
    ) -> None:
        field = next(f for f in schema.fields if f.custom["columnName"] != f.name)
        path = filled_workbook([valid_child])
        column = [f.name for f in schema.fields].index(field.name) + 2
        edit(path, lambda sheet: sheet.cell(1, column, field.custom["columnName"]))

        workbook = UploadWorkbook(path, schema)

        assert field.name in workbook.columns
        assert workbook.unknown_columns == []

    def test_recognises_an_earlier_column_name(
        self, schema: Schema, filled_workbook: Filler, valid_child: dict[str, Any]
    ) -> None:
        field = next(f for f in schema.fields if f.custom["earlierColumnNames"])
        path = filled_workbook([valid_child])
        column = [f.name for f in schema.fields].index(field.name) + 2
        earlier = field.custom["earlierColumnNames"][0]
        edit(path, lambda sheet: sheet.cell(1, column, earlier))

        workbook = UploadWorkbook(path, schema)

        assert field.name in workbook.columns
        assert workbook.unknown_columns == []

    def test_matches_the_first_column_to_no_field(
        self, schema: Schema, filled_workbook: Filler, valid_child: dict[str, Any]
    ) -> None:
        field = schema.fields[0]
        path = edit(
            filled_workbook([valid_child]),
            lambda sheet: sheet.cell(1, 1, field.name),
        )

        workbook = UploadWorkbook(path, schema)

        assert workbook.columns[field.name] != 0
        assert workbook.duplicate_columns == []


class TestCheckError:
    @pytest.mark.parametrize("suffix", [".xls", ".ods", ".csv", ""])
    def test_refuses_a_path_that_is_not_an_xlsx_workbook(
        self, schema: Schema, tmp_path: Path, suffix: str
    ) -> None:
        path = tmp_path / f"workbook{suffix}"
        path.write_bytes(b"anything")

        with pytest.raises(CheckError):
            UploadWorkbook(path, schema)

    @pytest.mark.parametrize("suffix", [".XLSX", ".xlsm"])
    def test_accepts_an_xlsx_suffix_in_any_case_and_xlsm(
        self,
        schema: Schema,
        filled_workbook: Filler,
        valid_child: dict[str, Any],
        tmp_path: Path,
        suffix: str,
    ) -> None:
        path = filled_workbook([valid_child])
        copy = tmp_path / f"copy{suffix}"
        copy.write_bytes(path.read_bytes())

        workbook = UploadWorkbook(copy, schema)

        assert workbook.header_row == 1

    def test_refuses_a_file_that_is_not_a_workbook(
        self, schema: Schema, tmp_path: Path
    ) -> None:
        path = tmp_path / "workbook.xlsx"
        path.write_bytes(b"this is not a zip file")

        with pytest.raises(CheckError):
            UploadWorkbook(path, schema)

    def test_refuses_a_file_that_does_not_exist(
        self, schema: Schema, tmp_path: Path
    ) -> None:
        with pytest.raises(CheckError):
            UploadWorkbook(tmp_path / "missing.xlsx", schema)

    def test_refuses_a_workbook_with_no_data_list_sheet(
        self, schema: Schema, tmp_path: Path
    ) -> None:
        path = tmp_path / "workbook.xlsx"
        workbook = Workbook()
        workbook.active.title = "readme"  # type: ignore[union-attr]
        workbook.save(path)

        with pytest.raises(CheckError):
            UploadWorkbook(path, schema)

    def test_refuses_a_data_list_sheet_with_no_header(
        self, schema: Schema, tmp_path: Path
    ) -> None:
        path = tmp_path / "workbook.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        assert sheet is not None
        sheet.title = "data list"
        sheet.append(["alpha", "beta", "gamma"])
        workbook.save(path)

        with pytest.raises(CheckError):
            UploadWorkbook(path, schema)

    def test_refuses_an_empty_data_list_sheet(
        self, schema: Schema, tmp_path: Path
    ) -> None:
        path = tmp_path / "workbook.xlsx"
        workbook = Workbook()
        workbook.active.title = "data list"  # type: ignore[union-attr]
        workbook.save(path)

        with pytest.raises(CheckError):
            UploadWorkbook(path, schema)
