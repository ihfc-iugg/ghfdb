import shutil
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import responses
from conftest import LARGE_CHILDREN, SEEDED_EVERY, read_problems
from frictionless import Schema
from openpyxl import Workbook, load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from ghfdb.cli import main
from ghfdb.qc.check import Kind
from ghfdb.qc.rules import CF_3, Condition
from ghfdb.template import FIRST_DATA_ROW

SOURCE = Path(__file__).parent / "sources" / "upload-template.xlsx"
Filler = Callable[[Sequence[Mapping[str, Any]]], Path]


def report_of(workbook: Path) -> Path:
    return workbook.with_name(f"{workbook.stem}.report.html")


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
        assert read_problems(report_of(path)) == []
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
        assert {(line[0], line[1]) for line in read_problems(report_of(path))} == {
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
        assert [line[0] for line in read_problems(report_of(path))] == [None]

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
        assert {(line[0], line[1]) for line in read_problems(report_of(path))} == {
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


BOREHOLE_METHOD = "[Drilling]"
PROBING_METHOD = "[Probing (onshore, lake, river, etc.)]"
LITERATURE_LOCATION = "[Literature or unspecified]"
CORE_SAMPLES_SOURCE = "[Core samples]"
EGRT_METHOD = "[EGRT]"
POINT_SOURCE_METHOD = "[Lab - point source]"


@pytest.mark.usefixtures("vocabularies_cached")
class TestRules:
    def test_reports_a_child_breaking_each_rule_and_no_other_problem(
        self, filled_workbook: Filler, valid_child: dict[str, Any]
    ) -> None:
        path = filled_workbook(
            [
                valid_child,
                valid_child | {"P12": BOREHOLE_METHOD, "C5": None},
                valid_child | {"P12": PROBING_METHOD, "C6": None},
                valid_child | {"C42": LITERATURE_LOCATION, "C41": CORE_SAMPLES_SOURCE},
                valid_child | {"C32": EGRT_METHOD, "C43": POINT_SOURCE_METHOD},
            ]
        )

        status = main(["check", str(path)])

        assert status == 1
        found = read_problems(report_of(path))
        assert [(line[0], line[1], line[3]) for line in found] == [
            (10, "C5", str(Kind.RULE)),
            (11, "C6", str(Kind.RULE)),
            (12, "C41", str(Kind.RULE)),
            (13, "C43", str(Kind.RULE)),
        ]
        assert [line[6].split()[0] for line in found] == [
            "CF-1",
            "CF-2",
            "CF-3",
            "CF-4",
        ]

    def test_a_rule_whose_concept_is_not_published_gives_status_2_naming_the_rule(
        self,
        monkeypatch: pytest.MonkeyPatch,
        filled_workbook: Filler,
        valid_child: dict[str, Any],
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        withdrawn = CF_3.then.concepts[0] + "_withdrawn"
        broken = replace(CF_3, then=Condition("C41", (withdrawn,)))
        monkeypatch.setattr("ghfdb.cli.RULES", (broken,))
        path = filled_workbook([valid_child])

        status = main(["check", str(path)])

        captured = capsys.readouterr()
        assert status == 2
        assert "CF-3" in captured.err
        assert not report_of(path).exists()


def column_of(sheet: Worksheet, code: str) -> int:
    """Find the column whose header, in row 1, is a field code."""
    return next(int(cell.column) for cell in sheet[1] if cell.value == code)


class TestEndToEnd:
    @pytest.fixture
    def seeded(
        self,
        schema: Schema,
        filled_workbook: Filler,
        valid_child: dict[str, Any],
        mandatory_code: str,
    ) -> tuple[Path, set[tuple[Any, ...]]]:
        """A workbook with one problem of each kind, and what should be reported."""
        number = next(
            f
            for f in schema.fields
            if f.type == "number" and {"minimum", "maximum"} <= set(f.constraints)
        )
        vocabulary = next(
            f
            for f in schema.fields
            if "enum" in f.constraints and f.name != mandatory_code
        )
        absent = next(
            f
            for f in schema.fields
            if f.custom["obligation"] == "R"
            and f.name not in {number.name}
            and f.name not in {vocabulary.name}
        )
        children = [
            valid_child | {mandatory_code: None},
            valid_child | {number.name: "not a number"},
            valid_child | {number.name: number.constraints["maximum"] + 1},
            valid_child | {vocabulary.name: "zzz-not-a-term"},
        ]
        path = filled_workbook(children)
        workbook = load_workbook(path)
        sheet = workbook["data list"]
        column = column_of(sheet, absent.name)
        for row in range(1, sheet.max_row + 1):
            sheet.cell(row, column).value = None
        last = sheet.max_column
        sheet.cell(1, last + 1, "Not a field")
        sheet.cell(9, last + 1, "x")
        sheet.cell(1, last + 2, number.name)
        workbook.save(path)
        return path, {
            (9, mandatory_code, str(Kind.MISSING)),
            (10, number.name, str(Kind.WRONG_TYPE)),
            (11, number.name, str(Kind.OUT_OF_RANGE)),
            (12, vocabulary.name, str(Kind.NOT_IN_VOCABULARY)),
            (None, None, str(Kind.UNKNOWN_COLUMN)),
            (None, number.name, str(Kind.DUPLICATE_COLUMN)),
            (None, absent.name, str(Kind.NO_COLUMN)),
        }

    @pytest.mark.usefixtures("vocabularies_cached")
    def test_reports_every_seeded_problem_and_no_other(
        self, seeded: tuple[Path, set[tuple[Any, ...]]]
    ) -> None:
        path, expected = seeded

        assert main(["check", str(path)]) == 1

        found = read_problems(report_of(path))
        assert {(line[0], line[1], line[3]) for line in found} == expected
        assert len(found) == len(expected)

    @pytest.mark.usefixtures("vocabularies_cached")
    @pytest.mark.parametrize(
        ("code", "misspelled"), [("C46", "tc_pT_fuction"), ("C49", "Ref_ISGN")]
    )
    def test_a_misspelled_published_name_is_an_unknown_column_with_the_right_name(
        self,
        schema: Schema,
        filled_workbook: Filler,
        valid_child: dict[str, Any],
        code: str,
        misspelled: str,
    ) -> None:
        path = filled_workbook([valid_child])
        workbook = load_workbook(path)
        sheet = workbook["data list"]
        sheet.cell(1, column_of(sheet, code)).value = misspelled
        workbook.save(path)

        main(["check", str(path)])

        found = read_problems(report_of(path))
        by_column = {line[3]: line for line in found if line[0] is None}
        unknown, absent = by_column["unknown column"], by_column["no column"]
        assert (unknown[2], unknown[5]) == (
            misspelled,
            schema.get_field(code).custom["columnName"],
        )
        assert absent[1] == code

    @pytest.mark.usefixtures("vocabularies_cached")
    def test_the_same_valid_data_in_the_hand_maintained_template_has_no_problem(
        self, schema: Schema, tmp_path: Path, valid_child: dict[str, Any]
    ) -> None:
        path = tmp_path / "template.xlsx"
        shutil.copyfile(SOURCE, path)
        workbook = load_workbook(path)
        sheet = workbook["data list"]
        for code, value in valid_child.items():
            sheet.cell(FIRST_DATA_ROW, column_of(sheet, code), value)
        workbook.save(path)

        assert main(["check", str(path)]) == 0
        assert read_problems(report_of(path)) == []


@pytest.mark.slow
@pytest.mark.usefixtures("vocabularies_cached")
class TestSpeed:
    LIMIT = 15

    def test_a_workbook_of_90000_children_is_checked_and_reported_in_time(
        self, large_workbook: tuple[Path, int]
    ) -> None:
        path, seeded = large_workbook

        started = time.perf_counter()
        status = main(["check", str(path)])
        elapsed = time.perf_counter() - started

        print(f"checked 90,000 children in {elapsed:.1f} s")
        assert status == 1
        assert elapsed < self.LIMIT
        found = read_problems(report_of(path))
        assert len(found) == seeded
        broken = LARGE_CHILDREN // SEEDED_EVERY
        assert [line[3] for line in found].count(str(Kind.RULE)) == broken
        assert len(found) - broken == broken
