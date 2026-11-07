"""The report a check writes beside the workbook, a single web page."""

import contextlib
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas
from jinja2 import Environment, PackageLoader
from markupsafe import Markup

from ghfdb import __version__
from ghfdb.fields import Vocabularies
from ghfdb.qc.rules import RULES
from ghfdb.qc.workbook import CheckError

TEMPLATES = Environment(loader=PackageLoader("ghfdb.qc", "templates"), autoescape=True)

HEADINGS = [
    "Excel row",
    "Field code",
    "Published column name",
    "Kind",
    "Value",
    "Suggestion",
    "Rule",
    "Related",
]
RULE_REFERENCE = "https://ihfc-iugg.github.io/ghfdb/reference/rules.html"
STATEMENTS = {rule.identifier: rule.statement for rule in RULES}
RULE_COLUMN = HEADINGS.index("Rule")
SCHEME_REFERENCE = "https://ihfc-iugg.github.io/ghfdb/reference/quality-scheme/"
# The heading of each column of the scores table and the page of the scheme reference
# that explains it, if any.
SCORE_PAGES = {
    "Excel row": None,
    "Rules": "index",
    "U-score": "u-score",
    "T-score": "index",
    "TC-score": "index",
    "M-score": "m-score",
    "Perturbation flags": "perturbation-flags",
    "Quality code": "index",
    "Has problems": None,
}
SCORE_HEADINGS = list(SCORE_PAGES)
SCORE_COLUMNS = ["rules", "U", "T", "TC", "M", "flags", "code"]
YES = "yes"
NO = "no"


class Report:
    """The problems a check found and what it was checked against.

    The report holds no copy of the data: the problems with the values they were
    found in, and a summary.

    Args:
        workbook_path: The workbook that was checked.
        problems: One line for each problem, with the columns ``row``, ``code``,
            ``column_name``, ``kind``, ``value``, ``suggestion``, ``rule`` and
            ``related``. A problem of the workbook's columns comes first and has no
            row. A problem of kind ``rule`` shows its rule's identifier, linked to the
            rule in the latest published reference, with the rule's statement, and the
            field that made the rule apply. Other kinds leave both cells empty.
        children: The number of children checked.
        vocabularies: The vocabularies the check read, which name the releases the
            report states.
        scores: The preview scores of the children, as ``Dataset.scores`` returns
            them, indexed by Excel row. A score not determined is an empty cell.

    Attributes:
        workbook_path: The workbook.
        problems: The problems.
        children: The number of children.
        vocabularies: The vocabularies.
        scores: The preview scores.
    """

    def __init__(
        self,
        workbook_path: Path,
        problems: pandas.DataFrame,
        children: int,
        vocabularies: Vocabularies,
        scores: pandas.DataFrame,
    ) -> None:
        self.workbook_path = workbook_path
        self.problems = problems
        self.children = children
        self.vocabularies = vocabularies
        self.scores = scores

    @property
    def path(self) -> Path:
        """Where the report is written: ``<workbook name>.report.html`` beside it."""
        return self.workbook_path.with_name(f"{self.workbook_path.stem}.report.html")

    def write(self) -> Path:
        """Write the report, replacing an earlier one.

        The report is written to a temporary file in the same folder and moved over
        the earlier report, so a report that cannot be written leaves the earlier one
        whole.

        Returns:
            The path of the report.

        Raises:
            CheckError: The report cannot be written. The message names the report.
        """
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                delete=False, dir=self.path.parent, suffix=".html"
            ) as file:
                temporary = Path(file.name)
            self.build(temporary)
            # A temporary file is readable by its owner only. The report gets the
            # mode any new file in the folder would have.
            umask = os.umask(0)
            os.umask(umask)
            temporary.chmod(0o666 & ~umask)
            os.replace(temporary, self.path)
        except OSError as error:
            if temporary is not None:
                with contextlib.suppress(OSError):
                    temporary.unlink()
            raise CheckError(f"{self.path} cannot be written: {error}") from error
        return self.path

    def build(self, path: Path) -> None:
        """Render the page and write it to a file.

        Args:
            path: The file to write.
        """
        page = TEMPLATES.get_template("report.html.jinja").render(
            workbook=self.workbook_path.name,
            summary=self.summary(),
            headings=HEADINGS,
            problems=self.cells(),
            score_headings=[
                (heading, f"{SCHEME_REFERENCE}{page}.html" if page else None)
                for heading, page in SCORE_PAGES.items()
            ],
            scores=self.score_rows(),
        )
        path.write_text(page, encoding="utf-8")

    def cells(self) -> list[list[dict[str, str]]]:
        """List the problems as text, an absent value as an empty cell.

        Returns:
            One list of eight cells for each problem, in the order of the problems.
            A cell is its ``text``, and for a rule its ``link`` to the rule reference
            and the rule's ``statement``.
        """
        return [
            [self.cell(position, cell) for position, cell in enumerate(problem)]
            for problem in self.problems.itertuples(index=False)
        ]

    def score_rows(self) -> list[Markup]:
        """List the preview scores as table rows, one for each child.

        Returns:
            For each child, in the order of the scores, its cells escaped and joined as
            the cells of a row: the Excel row, the scores as text with an empty cell
            for a score not determined, and whether the child has problems.
        """
        text = self.scores[SCORE_COLUMNS].astype(object)
        text["T"] = self.scores["T"].round(3).astype("string")
        text["TC"] = self.scores["TC"].round(3).astype("string")
        text = text.where(text.notna(), "")
        text.insert(0, "row", self.scores.index.astype(str))
        has_problems = self.scores.index.isin(self.problems["row"].dropna())
        text["problems"] = pandas.Series(has_problems, index=text.index).map(
            {True: YES, False: NO}
        )
        separator = Markup("</td><td>")
        return [separator.join(row) for row in text.itertuples(index=False)]

    @staticmethod
    def cell(position: int, value: Any) -> dict[str, str]:
        """Turn a value of the problem table into a cell of the report.

        Args:
            position: The value's column in the problem table.
            value: The value, which may be absent.

        Returns:
            The cell, which links the identifier of a rule to its reference entry.
        """
        text = "" if pandas.isna(value) else str(value)
        cell = {"text": text}
        if position == RULE_COLUMN and text:
            cell["link"] = f"{RULE_REFERENCE}#{text.lower()}"
            cell["statement"] = STATEMENTS.get(text, "")
        return cell

    def summary(self) -> list[tuple[str, str]]:
        """List what the summary states.

        Returns:
            A label and a value for each line of the summary.
        """
        rows = self.problems["row"].dropna().nunique()
        return [
            ("Workbook", self.workbook_path.name),
            ("ghfdb version", __version__),
            ("Checked at (UTC)", datetime.now(UTC).isoformat(timespec="seconds")),
            ("Vocabulary releases", ", ".join(self.vocabularies.releases())),
            ("Children", str(self.children)),
            ("Problems", str(len(self.problems))),
            ("Children with problems", str(int(rows))),
            (
                "Quality scheme",
                Markup('<a href="{}">GHFDB quality scheme</a>').format(
                    f"{SCHEME_REFERENCE}index.html"
                ),
            ),
        ]
