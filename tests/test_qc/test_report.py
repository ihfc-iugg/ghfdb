import contextlib
import os
import re
import stat
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas
import pytest
from conftest import read_headings, read_problems, read_scores, read_table
from frictionless import Schema

import ghfdb
from ghfdb.fields import Vocabularies
from ghfdb.qc.check import PROBLEM_COLUMNS, Kind
from ghfdb.qc.report import NO, SCORE_HEADINGS, YES, Report
from ghfdb.qc.rules import CF_1, CF_3
from ghfdb.qc.workbook import CheckError


def problem_table(*lines: dict[str, Any]) -> pandas.DataFrame:
    """Build a problem table; a line names only the columns it fills."""
    frame = pandas.DataFrame(list(lines), columns=PROBLEM_COLUMNS)
    return frame.astype({"row": "Int64"} | dict.fromkeys(PROBLEM_COLUMNS[1:], "string"))


def score_table(*children: dict[str, Any]) -> pandas.DataFrame:
    """Build the scores of children by Excel row; a child names only what it has.

    Each mapping holds ``row`` and any of the columns of ``Dataset.scores``. What a
    child leaves out is not determined.
    """
    numbers = ["T", "TC", "own_T", "own_TC"]
    marks = ["marked", "own_T_marked", "own_TC_marked"]
    texts = ["rules", "U", "M", "flags", "code"]
    frame = pandas.DataFrame(
        list(children), columns=["row", *texts, *numbers, *marks]
    ).set_index("row")
    return frame.astype(
        dict.fromkeys(texts, "string")
        | dict.fromkeys(numbers, "Float64")
        | dict.fromkeys(marks, "boolean")
    )


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
        report = Report(
            workbook_path, problem_table(), 3, published_vocabularies, score_table()
        )

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

        path = Report(
            workbook_path, problems, 1, published_vocabularies, score_table()
        ).write()

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

        path = Report(
            workbook_path, problems, 1, published_vocabularies, score_table()
        ).write()

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

        path = Report(
            workbook_path, problems, 17, published_vocabularies, score_table()
        ).write()

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

        path = Report(
            workbook_path, problem_table(), 1, published_vocabularies, score_table()
        ).write()

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

        path = Report(
            workbook_path, problem_table(), 1, published_vocabularies, score_table()
        ).write()

        assert stat.S_IMODE(path.stat().st_mode) == 0o666 & ~umask

    def test_a_check_with_no_problem_leaves_the_problems_table_empty(
        self, workbook_path: Path, published_vocabularies: Vocabularies
    ) -> None:
        path = Report(
            workbook_path, problem_table(), 4, published_vocabularies, score_table()
        ).write()

        assert read_problems(path) == []
        assert "0" in summary_values(path)

    def test_replaces_an_earlier_report(
        self, workbook_path: Path, published_vocabularies: Vocabularies
    ) -> None:
        first = problem_table({"row": 9, "code": "P1", "kind": Kind.MISSING})
        Report(workbook_path, first, 1, published_vocabularies, score_table()).write()

        path = Report(
            workbook_path, problem_table(), 1, published_vocabularies, score_table()
        ).write()

        assert read_problems(path) == []


def links_of(path: Path) -> list[str]:
    """List the address of every link in the report."""
    return re.findall(r'<a href="([^"]*)"', path.read_text(encoding="utf-8"))


class TestRuleProblems:
    @pytest.fixture
    def written(
        self, workbook_path: Path, published_vocabularies: Vocabularies
    ) -> Path:
        problems = problem_table(
            {"row": 9, "code": "P1", "kind": Kind.MISSING},
            {
                "row": 9,
                "code": "C5",
                "column_name": "q_bottom",
                "kind": Kind.RULE,
                "rule": CF_1.identifier,
                "related": "P12 explo_method [Drilling]",
            },
            {
                "row": 10,
                "code": "C41",
                "kind": Kind.RULE,
                "value": "[Core samples]",
                "rule": CF_3.identifier,
                "related": "C42 conductivity_location [Literature or unspecified]",
            },
        )
        return Report(
            workbook_path, problems, 2, published_vocabularies, score_table()
        ).write()

    def test_a_rule_problem_shows_its_identifier_its_statement_and_the_related_value(
        self, written: Path
    ) -> None:
        found = read_problems(written)

        assert [(line[0], line[1], line[3]) for line in found] == [
            (9, "P1", str(Kind.MISSING)),
            (9, "C5", str(Kind.RULE)),
            (10, "C41", str(Kind.RULE)),
        ]
        assert found[1][6].startswith(CF_1.identifier)
        assert CF_1.statement in found[1][6]
        assert found[1][7] == "P12 explo_method [Drilling]"
        assert found[2][6].startswith(CF_3.identifier)
        assert CF_3.statement in found[2][6]

    def test_other_kinds_have_no_rule_and_no_related_value(self, written: Path) -> None:
        assert read_problems(written)[0][6:] == (None, None)

    def test_the_identifier_links_to_its_lowercased_anchor_in_the_published_reference(
        self, written: Path
    ) -> None:
        reference = "https://ihfc-iugg.github.io/ghfdb/reference/rules.html"

        rule_links = [link for link in links_of(written) if link.startswith(reference)]
        assert rule_links == [f"{reference}#cf-1", f"{reference}#cf-3"]


SCHEME_PAGES = Path(__file__).parents[2] / "docs" / "reference" / "quality-scheme"
SCHEME_URL = "https://ihfc-iugg.github.io/ghfdb/reference/quality-scheme/"


def page_of(address: str) -> Path:
    """Find the source page of the scheme reference a published address names."""
    assert address.startswith(SCHEME_URL)
    return SCHEME_PAGES / address.removeprefix(SCHEME_URL).replace(".html", ".md")


class TestPreviewScores:
    @pytest.fixture
    def written(
        self, workbook_path: Path, published_vocabularies: Vocabularies
    ) -> Path:
        scores = score_table(
            {
                "row": 9,
                "rules": "probe sensing",
                "U": "U1",
                "T": 1.1,
                "TC": 0.9,
                "marked": True,
                "M": "M1x",
                "flags": "-------",
                "code": "U1.M1x.-------",
            },
            {
                "row": 10,
                "U": "Ux",
                "M": "Mx",
                "flags": "-------",
                "code": "Ux.Mx.-------",
            },
        )
        problems = problem_table({"row": 10, "code": "P1", "kind": Kind.MISSING})
        return Report(
            workbook_path, problems, 2, published_vocabularies, scores
        ).write()

    def test_each_child_has_a_row_with_its_scores_under_the_headings(
        self, written: Path
    ) -> None:
        first, second = read_scores(written)

        assert (first["Excel row"], second["Excel row"]) == ("9", "10")
        assert first["Rules"] == "probe sensing"
        assert first["U-score"] == "U1"
        assert float(first["T-score"]) == pytest.approx(1.1)
        assert float(first["TC-score"]) == pytest.approx(0.9)
        assert first["M-score"] == "M1x"
        assert first["Perturbation flags"] == "-------"
        assert first["Quality code"] == "U1.M1x.-------"

    def test_a_score_not_determined_is_an_empty_cell_never_zero(
        self, written: Path
    ) -> None:
        second = read_scores(written)[1]

        assert second["Rules"] == ""
        assert second["T-score"] == ""
        assert second["TC-score"] == ""

    def test_says_which_children_have_problems(self, written: Path) -> None:
        first, second = read_scores(written)

        assert first["Has problems"] == NO
        assert second["Has problems"] == YES

    def test_a_check_of_no_children_has_the_headings_and_no_rows(
        self, workbook_path: Path, published_vocabularies: Vocabularies
    ) -> None:
        path = Report(
            workbook_path, problem_table(), 0, published_vocabularies, score_table()
        ).write()

        assert read_scores(path) == []
        assert [text for text, _ in read_headings(path, "scores")] == SCORE_HEADINGS

    def test_a_value_holding_markup_is_written_escaped(
        self, workbook_path: Path, published_vocabularies: Vocabularies
    ) -> None:
        value = '<script>alert(1)</script> & "quoted"'
        scores = score_table({"row": 9, "rules": value})

        path = Report(
            workbook_path, problem_table(), 1, published_vocabularies, scores
        ).write()

        assert read_scores(path)[0]["Rules"] == value
        assert "<script" not in path.read_text(encoding="utf-8")

    def test_each_score_heading_links_to_a_page_of_the_scheme_reference(
        self, written: Path
    ) -> None:
        links = dict(read_headings(written, "scores"))

        for heading in SCORE_HEADINGS:
            if heading in {"Excel row", "Has problems"}:
                continue
            link = links[heading]
            assert link is not None, heading
            assert page_of(link).is_file(), heading

    def test_the_summary_links_to_the_overview_of_the_scheme(
        self, written: Path
    ) -> None:
        assert f"{SCHEME_URL}index.html" in links_of(written)
        assert page_of(f"{SCHEME_URL}index.html").is_file()


class TestReportFailure:
    def test_a_report_path_that_cannot_be_replaced_is_a_check_error(
        self, workbook_path: Path, published_vocabularies: Vocabularies
    ) -> None:
        workbook_path.with_name("my-data.report.html").mkdir()
        report = Report(
            workbook_path, problem_table(), 1, published_vocabularies, score_table()
        )

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
            workbook_path, problem_table(), 1, published_vocabularies, score_table()
        ).write()
        before = earlier.read_bytes()

        def refuse(self: Report, path: Path) -> None:
            raise OSError("refused")

        monkeypatch.setattr(Report, "build", refuse)
        report = Report(
            workbook_path, problem_table(), 1, published_vocabularies, score_table()
        )

        with pytest.raises(CheckError, match="my-data.report.html"):
            report.write()

        assert earlier.read_bytes() == before
        assert sorted(p.name for p in workbook_path.parent.iterdir()) == [
            "my-data.report.html",
            "my-data.xlsx",
        ]
