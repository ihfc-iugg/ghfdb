import shutil
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest
import responses
from frictionless import Schema
from openpyxl import Workbook, load_workbook

from ghfdb.cli import main

Filler = Callable[[Sequence[Mapping[str, Any]]], Path]


def report_of(workbook: Path) -> Path:
    return workbook.with_name(f"{workbook.stem}.report.xlsx")


def problem_lines(report: Path) -> list[tuple[Any, ...]]:
    sheet = load_workbook(report)["problems"]
    return [tuple(cell.value for cell in row) for row in sheet.iter_rows(min_row=2)]


@pytest.fixture
def mandatory_code(schema: Schema) -> str:
    """The code of a field every child must fill in."""
    return next(
        field.name
        for field in schema.fields
        if field.custom["obligation"] == "M"
        and set(field.custom["domain"]) == {"B", "S"}
        and field.type == "string"
    )


@pytest.mark.usefixtures("vocabularies_cached")
class TestMain:
    def test_a_workbook_with_no_problem_gives_status_0_and_a_report(
        self,
        filled_workbook: Filler,
        valid_child: dict[str, Any],
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        path = filled_workbook([valid_child, valid_child])

        status = main(["check", str(path)])

        assert status == 0
        assert problem_lines(report_of(path)) == []
        assert str(report_of(path)) in capsys.readouterr().out

    def test_a_workbook_with_a_problem_gives_status_1(
        self,
        filled_workbook: Filler,
        valid_child: dict[str, Any],
        mandatory_code: str,
    ) -> None:
        path = filled_workbook([valid_child | {mandatory_code: None}])

        status = main(["check", str(path)])

        assert status == 1
        assert {(line[0], line[1]) for line in problem_lines(report_of(path))} == {
            (9, mandatory_code)
        }

    def test_puts_the_workbook_s_column_problems_in_the_report(
        self,
        filled_workbook: Filler,
        valid_child: dict[str, Any],
    ) -> None:
        path = filled_workbook([valid_child])
        workbook = load_workbook(path)
        sheet = workbook["data list"]
        sheet.cell(1, sheet.max_column + 1, "Not a field")
        sheet.cell(9, sheet.max_column, "x")
        workbook.save(path)

        status = main(["check", str(path)])

        assert status == 1
        assert [line[0] for line in problem_lines(report_of(path))] == [None]

    @pytest.mark.parametrize("name", ["missing.xlsx", "notes.txt"])
    def test_a_file_that_cannot_be_read_gives_status_2_and_no_report(
        self,
        name: str,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        path = tmp_path / name
        if name.endswith(".txt"):
            path.write_text("not a workbook")

        status = main(["check", str(path)])

        captured = capsys.readouterr()
        assert status == 2
        assert captured.err.strip()
        assert captured.out == ""
        assert not report_of(path).exists()

    def test_a_workbook_with_no_data_list_sheet_gives_status_2(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = tmp_path / "other.xlsx"
        workbook_with_sheet("elsewhere", path)

        status = main(["check", str(path)])

        assert status == 2
        assert capsys.readouterr().err.strip()

    def test_a_report_that_cannot_be_written_gives_status_2(
        self,
        filled_workbook: Filler,
        valid_child: dict[str, Any],
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        path = filled_workbook([valid_child])
        report_of(path).mkdir()

        status = main(["check", str(path)])

        assert status == 2
        assert capsys.readouterr().err.strip()


def workbook_with_sheet(title: str, path: Path) -> Path:
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.title = title
    workbook.save(path)
    return path


class TestWorkbookUnchanged:
    def test_a_run_with_problems_leaves_the_workbook_as_it_was(
        self,
        vocabularies_cached: Path,
        filled_workbook: Filler,
        valid_child: dict[str, Any],
        mandatory_code: str,
    ) -> None:
        path = filled_workbook([valid_child | {mandatory_code: None}])
        before = path.read_bytes()

        assert main(["check", str(path)]) == 1

        assert path.read_bytes() == before

    def test_a_run_with_no_problem_leaves_the_workbook_as_it_was(
        self,
        vocabularies_cached: Path,
        filled_workbook: Filler,
        valid_child: dict[str, Any],
    ) -> None:
        path = filled_workbook([valid_child])
        before = path.read_bytes()

        assert main(["check", str(path)]) == 0

        assert path.read_bytes() == before

    def test_a_run_whose_report_cannot_be_written_leaves_the_workbook_as_it_was(
        self,
        vocabularies_cached: Path,
        filled_workbook: Filler,
        valid_child: dict[str, Any],
    ) -> None:
        path = filled_workbook([valid_child])
        report_of(path).mkdir()
        before = path.read_bytes()

        assert main(["check", str(path)]) == 2

        assert path.read_bytes() == before

    def test_a_report_path_that_links_to_the_workbook_leaves_it_as_it_was(
        self,
        vocabularies_cached: Path,
        filled_workbook: Filler,
        valid_child: dict[str, Any],
    ) -> None:
        path = filled_workbook([valid_child])
        report_of(path).symlink_to(path)
        before = path.read_bytes()

        main(["check", str(path)])

        assert path.read_bytes() == before


class TestOffline:
    def test_the_cached_vocabularies_give_the_same_problems_without_a_network(
        self,
        monkeypatch: pytest.MonkeyPatch,
        cache_directory: Path,
        schema: Schema,
        tmp_path: Path,
        web: responses.RequestsMock,
        filled_workbook: Filler,
        valid_child: dict[str, Any],
        mandatory_code: str,
    ) -> None:
        cache = tmp_path / "cache"
        shutil.copytree(cache_directory, cache)
        monkeypatch.setattr(
            "ghfdb.fields.vocabularies.user_cache_dir", lambda _: str(cache)
        )
        path = filled_workbook([valid_child | {mandatory_code: None}])

        status = main(["check", str(path)])

        assert status == 1
        assert {(line[0], line[1]) for line in problem_lines(report_of(path))} == {
            (9, mandatory_code)
        }

    def test_nothing_cached_and_no_network_gives_status_2(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        web: responses.RequestsMock,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr(
            "ghfdb.fields.vocabularies.user_cache_dir", lambda _: str(tmp_path / "none")
        )
        path = tmp_path / "workbook.xlsx"

        status = main(["check", str(path)])

        assert status == 2
        assert capsys.readouterr().err.strip()
        assert not report_of(path).exists()
