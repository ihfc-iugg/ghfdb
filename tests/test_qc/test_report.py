import contextlib
import os
import stat
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas
import pytest
from conftest import read_problems, read_table
from frictionless import Schema

import ghfdb
from ghfdb.fields import Vocabularies
from ghfdb.qc.check import PROBLEM_COLUMNS, Kind
from ghfdb.qc.report import Report
from ghfdb.qc.workbook import CheckError


def problem_table(*lines: dict[str, Any]) -> pandas.DataFrame:
    """Build a problem table; a line names only the columns it fills."""
    frame = pandas.DataFrame(list(lines), columns=PROBLEM_COLUMNS)
    return frame.astype({"row": "Int64"} | dict.fromkeys(PROBLEM_COLUMNS[1:], "string"))


def summary_values(path: Path) -> list[str]:
    """Read every cell of the summary table."""
    return [cell for row in read_table(path, "summary") for cell in row]


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

        assert path == workbook_path.with_name("my-data.report.html")
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
            (None, None, "Extra", str(Kind.UNKNOWN_COLUMN), None, None, None, None),
            (9, "P1", "Heat flow", str(Kind.WRONG_TYPE), "abc", "ab", None, None),
        ]

    def test_writes_a_value_holding_markup_escaped(
        self, workbook_path: Path, published_vocabularies: Vocabularies
    ) -> None:
        value = '<script>alert(1)</script> & "quoted"'
        problems = problem_table(
            {"row": 9, "code": "P1", "kind": Kind.WRONG_TYPE, "value": value}
        )

        path = Report(workbook_path, problems, 1, published_vocabularies).write()

        assert read_problems(path)[0][4] == value
        assert "<script" not in path.read_text(encoding="utf-8")

    def test_writes_the_counts_and_the_package_version(
        self, workbook_path: Path, published_vocabularies: Vocabularies
    ) -> None:
        problems = problem_table(
            {"row": 9, "code": "P1", "kind": Kind.MISSING},
            {"row": 9, "code": "P2", "kind": Kind.MISSING},
            {"row": 10, "code": "P1", "kind": Kind.MISSING},
        )

        path = Report(workbook_path, problems, 17, published_vocabularies).write()

        values = summary_values(path)
        assert workbook_path.name in values
        assert ghfdb.__version__ in values
        assert {"17", "3", "2"} <= set(values)

    def test_states_the_vocabulary_releases_and_the_time_of_the_check(
        self,
        workbook_path: Path,
        published_vocabularies: Vocabularies,
        schema: Schema,
    ) -> None:
        before = datetime.now(UTC).replace(microsecond=0)

        path = Report(workbook_path, problem_table(), 1, published_vocabularies).write()

        values = summary_values(path)
        releases = published_vocabularies.releases()
        assert releases
        assert all(any(release in value for value in values) for release in releases)
        times = []
        for value in values:
            with contextlib.suppress(ValueError):
                times.append(datetime.fromisoformat(value))
        assert any(
            before <= moment <= datetime.now(UTC) for moment in times if moment.tzinfo
        )

    @pytest.mark.skipif(os.name != "posix", reason="file modes are POSIX")
    def test_gives_the_report_the_mode_of_a_new_file(
        self, workbook_path: Path, published_vocabularies: Vocabularies
    ) -> None:
        umask = os.umask(0)
        os.umask(umask)

        path = Report(workbook_path, problem_table(), 1, published_vocabularies).write()

        assert stat.S_IMODE(path.stat().st_mode) == 0o666 & ~umask

    def test_a_check_with_no_problem_leaves_the_problems_table_empty(
        self, workbook_path: Path, published_vocabularies: Vocabularies
    ) -> None:
        path = Report(workbook_path, problem_table(), 4, published_vocabularies).write()

        assert read_problems(path) == []
        assert "0" in summary_values(path)

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
        workbook_path.with_name("my-data.report.html").mkdir()
        report = Report(workbook_path, problem_table(), 1, published_vocabularies)

        with pytest.raises(CheckError, match="my-data.report.html"):
            report.write()

        assert sorted(p.name for p in workbook_path.parent.iterdir()) == [
            "my-data.report.html",
            "my-data.xlsx",
        ]

    def test_a_failed_render_leaves_the_earlier_report_whole_and_no_temporary_file(
        self,
        workbook_path: Path,
        published_vocabularies: Vocabularies,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        earlier = Report(
            workbook_path, problem_table(), 1, published_vocabularies
        ).write()
        before = earlier.read_bytes()

        def refuse(self: Report, path: Path) -> None:
            raise OSError("refused")

        monkeypatch.setattr(Report, "build", refuse)
        report = Report(workbook_path, problem_table(), 1, published_vocabularies)

        with pytest.raises(CheckError, match="my-data.report.html"):
            report.write()

        assert earlier.read_bytes() == before
        assert sorted(p.name for p in workbook_path.parent.iterdir()) == [
            "my-data.report.html",
            "my-data.xlsx",
        ]
