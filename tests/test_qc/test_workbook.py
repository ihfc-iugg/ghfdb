from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import pandas
import pytest
import xlsxwriter
from frictionless import Schema
from openpyxl import Workbook, load_workbook
from openpyxl.utils import get_column_letter

from ghfdb.qc.workbook import CheckError, UploadWorkbook
from ghfdb.template import FIRST_DATA_ROW, ROW_LABELS

Filler = Callable[[Sequence[Mapping[str, Any]]], Path]
SOURCE = Path(__file__).parent.parent / "sources" / "upload-template.xlsx"


def write(path: Path, build: Callable[[Any], None], readme_first: bool = False) -> Path:
    """Write a workbook whose ``data list`` sheet is filled in by ``build``."""
    workbook = xlsxwriter.Workbook(path)
    if readme_first:
        workbook.add_worksheet("readme").write(0, 0, "readme")
    build(workbook.add_worksheet("data list"))
    workbook.close()
    return path


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


COLUMNS = ["row", "code", "column_name", "kind", "value", "suggestion"]


class TestUploadWorkbookData:
    def test_indexes_the_children_by_their_excel_row(
        self, schema: Schema, filled_workbook: Filler, valid_child: dict[str, Any]
    ) -> None:
        path = filled_workbook([valid_child, valid_child])

        data = UploadWorkbook(path, schema).data()

        assert data.index.name == "row"
        assert list(data.index) == [FIRST_DATA_ROW, FIRST_DATA_ROW + 1]
        assert list(data.columns) == [field.name for field in schema.fields]

    def test_reads_each_value_as_text(
        self, schema: Schema, filled_workbook: Filler, valid_child: dict[str, Any]
    ) -> None:
        field = next(f for f in schema.fields if f.type == "number")
        child = {**valid_child, field.name: "12.50"}

        data = UploadWorkbook(filled_workbook([child]), schema).data()

        assert data.loc[FIRST_DATA_ROW, field.name] == "12.50"

    def test_indexes_by_excel_row_in_a_sheet_that_starts_at_b3(
        self, schema: Schema, filled_workbook: Filler, valid_child: dict[str, Any]
    ) -> None:
        def move(sheet: Any) -> None:
            sheet.move_range(sheet.dimensions, rows=2, cols=1)

        path = edit(filled_workbook([valid_child, valid_child]), move)

        data = UploadWorkbook(path, schema).data()

        assert list(data.index) == [FIRST_DATA_ROW + 2, FIRST_DATA_ROW + 3]

    def test_keeps_every_field_in_its_own_column_with_a_stray_cell_in_column_a(
        self, schema: Schema, tmp_path: Path
    ) -> None:
        codes = [field.name for field in schema.fields[:3]]

        def build(sheet: Any) -> None:
            sheet.write_row(2, 1, ["ID", *codes])
            sheet.write_row(3, 1, ["1", "v0", "v1", "v2"])
            sheet.write(30, 0, "note")

        data = UploadWorkbook(write(tmp_path / "w.xlsx", build), schema).data()

        assert list(data.index) == [4]
        assert [data.loc[4, code] for code in codes] == ["v0", "v1", "v2"]

    def test_reads_a_cell_with_spaces_only_as_missing(
        self, schema: Schema, filled_workbook: Filler, valid_child: dict[str, Any]
    ) -> None:
        field = next(f for f in schema.fields if f.type == "string")
        child = {**valid_child, field.name: "   "}

        data = UploadWorkbook(filled_workbook([child]), schema).data()

        assert data[field.name].isna()[FIRST_DATA_ROW]

    def test_drops_a_row_with_every_field_empty_and_a_row_holding_only_an_id(
        self, schema: Schema, filled_workbook: Filler, valid_child: dict[str, Any]
    ) -> None:
        blank = {schema.fields[0].name: "  "}
        path = filled_workbook([valid_child, {"ID": "7"}, blank, valid_child])

        data = UploadWorkbook(path, schema).data()

        assert list(data.index) == [FIRST_DATA_ROW, FIRST_DATA_ROW + 3]

    def test_reads_a_formula_as_the_value_saved_for_it(
        self, schema: Schema, tmp_path: Path
    ) -> None:
        code = schema.fields[0].name

        def build(sheet: Any) -> None:
            sheet.write_row(0, 0, ["ID", code])
            sheet.write_formula(1, 1, "=3+4", None, "saved")

        data = UploadWorkbook(write(tmp_path / "w.xlsx", build), schema).data()

        assert data.loc[2, code] == "saved"

    def test_reads_a_formula_with_no_saved_value_as_empty(
        self, schema: Schema, tmp_path: Path
    ) -> None:
        fields = schema.fields[:2]
        path = tmp_path / "w.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        assert sheet is not None
        sheet.title = "data list"
        sheet.append(["ID", *[field.name for field in fields]])
        sheet.append([1, "=3+4", "kept"])
        workbook.save(path)

        data = UploadWorkbook(path, schema).data()

        assert data[fields[0].name].isna()[2]
        assert data.loc[2, fields[1].name] == "kept"

    @pytest.mark.parametrize("readme_first", [False, True])
    def test_reads_an_excel_error_value_as_its_text(
        self, schema: Schema, tmp_path: Path, readme_first: bool
    ) -> None:
        mandatory = next(f for f in schema.fields if f.custom["obligation"] == "M")
        other = next(f for f in schema.fields if f.name != mandatory.name)
        codes = [mandatory.name, other.name]

        def build(sheet: Any) -> None:
            sheet.write_row(0, 0, ["ID", *codes])
            sheet.write_formula(1, 1, "=NA()", None, "#N/A")
            sheet.write(1, 2, "kept")
            sheet.write_formula(2, 2, "=1/0", None, "#DIV/0!")

        path = write(tmp_path / "w.xlsx", build, readme_first)

        data = UploadWorkbook(path, schema).data()

        assert data.loc[2, mandatory.name] == "#N/A"
        assert data.loc[2, other.name] == "kept"
        assert data.loc[3, other.name] == "#DIV/0!"
        assert data[mandatory.name].isna()[3]

    def test_finds_an_error_value_in_a_sheet_starting_at_b3(
        self, schema: Schema, tmp_path: Path
    ) -> None:
        codes = [field.name for field in schema.fields[:2]]

        def build(sheet: Any) -> None:
            sheet.write_row(2, 1, ["ID", *codes])
            sheet.write_row(3, 1, ["1", "kept"])
            sheet.write_formula(3, 3, "=NA()", None, "#N/A")

        data = UploadWorkbook(write(tmp_path / "w.xlsx", build), schema).data()

        assert data.loc[4, codes[0]] == "kept"
        assert data.loc[4, codes[1]] == "#N/A"


class TestColumnProblems:
    def test_finds_none_in_the_templates(
        self, schema: Schema, filled_workbook: Filler, valid_child: dict[str, Any]
    ) -> None:
        for path in (filled_workbook([valid_child]), SOURCE):
            problems = UploadWorkbook(path, schema).column_problems()

            assert list(problems.columns) == COLUMNS
            assert problems.empty

    def test_finds_an_unknown_column_once_with_no_row(
        self, schema: Schema, filled_workbook: Filler, valid_child: dict[str, Any]
    ) -> None:
        width = len(schema.fields) + 2
        path = filled_workbook([valid_child, valid_child])
        edit(path, lambda sheet: sheet.cell(1, width, "Bogus"))
        edit(path, lambda sheet: sheet.cell(FIRST_DATA_ROW, width, "x"))
        edit(path, lambda sheet: sheet.cell(FIRST_DATA_ROW + 1, width, "y"))

        problems = UploadWorkbook(path, schema).column_problems()

        assert len(problems) == 1
        assert problems.iloc[0]["column_name"] == "Bogus"
        assert problems.iloc[0]["kind"] == "unknown column"
        assert pandas.isna(problems.iloc[0]["row"])

    def test_finds_a_column_with_no_header_that_holds_values_by_its_letter(
        self, schema: Schema, filled_workbook: Filler, valid_child: dict[str, Any]
    ) -> None:
        width = len(schema.fields) + 2
        path = edit(
            filled_workbook([valid_child]),
            lambda sheet: sheet.cell(FIRST_DATA_ROW, width, "x"),
        )

        problems = UploadWorkbook(path, schema).column_problems()

        assert list(problems["column_name"]) == [get_column_letter(width)]
        assert list(problems["kind"]) == ["unknown column"]

    def test_ignores_a_column_with_no_header_that_holds_nothing(
        self, schema: Schema, filled_workbook: Filler, valid_child: dict[str, Any]
    ) -> None:
        width = len(schema.fields) + 2
        path = edit(
            filled_workbook([valid_child]),
            lambda sheet: sheet.cell(FIRST_DATA_ROW, width, "   "),
        )

        problems = UploadWorkbook(path, schema).column_problems()

        assert problems.empty

    def test_finds_two_columns_for_one_field_and_uses_the_first(
        self, schema: Schema, filled_workbook: Filler, valid_child: dict[str, Any]
    ) -> None:
        field = schema.fields[0]
        width = len(schema.fields) + 2
        path = filled_workbook([{**valid_child, field.name: "first"}])
        edit(path, lambda sheet: sheet.cell(1, width, field.name))
        edit(path, lambda sheet: sheet.cell(FIRST_DATA_ROW, width, "second"))
        workbook = UploadWorkbook(path, schema)

        problems = workbook.column_problems()
        data = workbook.data()

        assert list(problems["code"]) == [field.name]
        assert list(problems["kind"]) == ["duplicate column"]
        assert pandas.isna(problems.iloc[0]["row"])
        assert data.loc[FIRST_DATA_ROW, field.name] == "first"
