from pathlib import Path
from typing import Any

import pandas
import pytest
import xlsxwriter
from openpyxl import load_workbook

import ghfdb
from ghfdb.fields import Vocabularies
from ghfdb.qc.check import PROBLEM_COLUMNS, Kind
from ghfdb.qc.report import Report
from ghfdb.qc.workbook import CheckError


def problem_table(*lines: dict[str, Any]) -> pandas.DataFrame:
    """Build a problem table; a line names only the columns it fills."""
    frame = pandas.DataFrame(list(lines), columns=PROBLEM_COLUMNS)
    return frame.astype({"row": "Int64"} | dict.fromkeys(PROBLEM_COLUMNS[1:], "string"))


def read_problems(path: Path) -> list[tuple[Any, ...]]:
    """Read the lines of the problems sheet, leaving out the heading row."""
    sheet = load_workbook(path)["problems"]
    return [tuple(cell.value for cell in row) for row in sheet.iter_rows(min_row=2)]


def cell_values(path: Path, sheet: str) -> list[Any]:
    return [
        cell.value
        for row in load_workbook(path)[sheet].iter_rows()
        for cell in row
        if cell.value is not None
    ]


@pytest.fixture
def workbook_path(tmp_path: Path) -> Path:
    path = tmp_path / "my-data.xlsx"
    path.write_bytes(b"the workbook")
    return path


class TestReportWrite:
    def test_writes_the_report_beside_the_workbook(
        self, workbook_path: Path, published_vocabularies: Vocabularies
    ) -> None:
        report = Report(workbook_path, problem_table(), 3, published_vocabularies)

        path = report.write()

        assert path == workbook_path.with_name("my-data.report.xlsx")
        assert path.is_file()

    def test_lists_column_problems_first_without_a_row(
        self, workbook_path: Path, published_vocabularies: Vocabularies
    ) -> None:
        problems = problem_table(
            {"column_name": "Extra", "kind": Kind.UNKNOWN_COLUMN},
            {
                "row": 9,
                "code": "P1",
                "column_name": "Heat flow",
                "kind": Kind.WRONG_TYPE,
                "value": "abc",
                "suggestion": "ab",
            },
        )

        path = Report(workbook_path, problems, 1, published_vocabularies).write()

        assert read_problems(path) == [
            (None, None, "Extra", str(Kind.UNKNOWN_COLUMN), None, None),
            (9, "P1", "Heat flow", str(Kind.WRONG_TYPE), "abc", "ab"),
        ]

    def test_writes_a_value_starting_with_equals_as_text(
        self, workbook_path: Path, published_vocabularies: Vocabularies
    ) -> None:
        problems = problem_table(
            {"row": 9, "code": "P1", "kind": Kind.WRONG_TYPE, "value": "=1+1"}
        )

        path = Report(workbook_path, problems, 1, published_vocabularies).write()

        cell = load_workbook(path)["problems"]["E2"]
        assert cell.data_type == "s"
        assert cell.value == "=1+1"

    def test_writes_the_counts_and_the_package_version(
        self, workbook_path: Path, published_vocabularies: Vocabularies
    ) -> None:
        problems = problem_table(
            {"row": 9, "code": "P1", "kind": Kind.MISSING},
            {"row": 9, "code": "P2", "kind": Kind.MISSING},
            {"row": 10, "code": "P1", "kind": Kind.MISSING},
        )

        path = Report(workbook_path, problems, 17, published_vocabularies).write()

        values = cell_values(path, "summary")
        assert workbook_path.name in values
        assert ghfdb.__version__ in values
        assert {17, 3, 2} <= set(values)

    def test_a_check_with_no_problem_leaves_the_problems_sheet_empty(
        self, workbook_path: Path, published_vocabularies: Vocabularies
    ) -> None:
        path = Report(workbook_path, problem_table(), 4, published_vocabularies).write()

        assert read_problems(path) == []
        assert 0 in cell_values(path, "summary")

    def test_replaces_an_earlier_report(
        self, workbook_path: Path, published_vocabularies: Vocabularies
    ) -> None:
        first = problem_table({"row": 9, "code": "P1", "kind": Kind.MISSING})
        Report(workbook_path, first, 1, published_vocabularies).write()

        path = Report(workbook_path, problem_table(), 1, published_vocabularies).write()

        assert read_problems(path) == []


class TestReportFailure:
    def test_a_report_path_that_cannot_be_replaced_is_a_check_error(
        self, workbook_path: Path, published_vocabularies: Vocabularies
    ) -> None:
        workbook_path.with_name("my-data.report.xlsx").mkdir()
        report = Report(workbook_path, problem_table(), 1, published_vocabularies)

        with pytest.raises(CheckError, match="my-data.report.xlsx"):
            report.write()

        assert sorted(p.name for p in workbook_path.parent.iterdir()) == [
            "my-data.report.xlsx",
            "my-data.xlsx",
        ]

    def test_a_failed_close_leaves_the_earlier_report_whole_and_no_temporary_file(
        self,
        workbook_path: Path,
        published_vocabularies: Vocabularies,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        earlier = Report(
            workbook_path, problem_table(), 1, published_vocabularies
        ).write()
        before = earlier.read_bytes()

        def refuse(self: xlsxwriter.Workbook) -> None:
            raise xlsxwriter.exceptions.XlsxFileError("refused")

        monkeypatch.setattr(xlsxwriter.Workbook, "close", refuse)
        report = Report(workbook_path, problem_table(), 1, published_vocabularies)

        with pytest.raises(CheckError, match="my-data.report.xlsx"):
            report.write()

        assert earlier.read_bytes() == before
        assert sorted(p.name for p in workbook_path.parent.iterdir()) == [
            "my-data.report.xlsx",
            "my-data.xlsx",
        ]
