"""The report a check writes beside the workbook, a single web page."""

import contextlib
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pandas
from jinja2 import Environment, PackageLoader

from ghfdb import __version__
from ghfdb.fields import Vocabularies
from ghfdb.qc.workbook import CheckError

TEMPLATES = Environment(loader=PackageLoader("ghfdb.qc", "templates"), autoescape=True)

HEADINGS = [
    "Excel row",
    "Field code",
    "Published column name",
    "Kind",
    "Value",
    "Suggestion",
]


class Report:
    """The problems a check found and what it was checked against.

    The report holds no copy of the data: the problems with the values they were
    found in, and a summary.

    Args:
        workbook_path: The workbook that was checked.
        problems: One line for each problem, with the columns ``row``, ``code``,
            ``column_name``, ``kind``, ``value`` and ``suggestion``. A problem of the
            workbook's columns comes first and has no row.
        children: The number of children checked.
        vocabularies: The vocabularies the check read, which name the releases the
            report states.

    Attributes:
        workbook_path: The workbook.
        problems: The problems.
        children: The number of children.
        vocabularies: The vocabularies.
    """

    def __init__(
        self,
        workbook_path: Path,
        problems: pandas.DataFrame,
        children: int,
        vocabularies: Vocabularies,
    ) -> None:
        self.workbook_path = workbook_path
        self.problems = problems
        self.children = children
        self.vocabularies = vocabularies

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
        )
        path.write_text(page, encoding="utf-8")

    def cells(self) -> list[list[str]]:
        """List the problems as text, an absent value as an empty cell.

        Returns:
            One list of six cells for each problem, in the order of the problems.
        """
        return [
            ["" if pandas.isna(cell) else str(cell) for cell in problem]
            for problem in self.problems.itertuples(index=False)
        ]

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
        ]
