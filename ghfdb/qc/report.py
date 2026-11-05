"""The report a check writes beside the workbook."""

import contextlib
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pandas
import xlsxwriter
from xlsxwriter.exceptions import XlsxFileError

from ghfdb import __version__
from ghfdb.fields import Vocabularies
from ghfdb.qc.workbook import CheckError

HEADINGS = [
    "Excel row",
    "Field code",
    "Published column name",
    "Kind",
    "Value",
    "Suggestion",
]
WIDTHS = [11, 12, 32, 20, 40, 40]


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
        """Where the report is written: ``<workbook name>.report.xlsx`` beside it."""
        return self.workbook_path.with_name(f"{self.workbook_path.stem}.report.xlsx")

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
                delete=False, dir=self.path.parent, suffix=".xlsx"
            ) as file:
                temporary = Path(file.name)
            self.build(temporary)
            # A temporary file is readable by its owner only. The report gets the
            # mode any new file in the folder would have.
            umask = os.umask(0)
            os.umask(umask)
            temporary.chmod(0o666 & ~umask)
            os.replace(temporary, self.path)
        except (OSError, XlsxFileError) as error:
            if temporary is not None:
                with contextlib.suppress(OSError):
                    temporary.unlink()
            raise CheckError(f"{self.path} cannot be written: {error}") from error
        return self.path

    def build(self, path: Path) -> None:
        """Write the ``problems`` and ``summary`` sheets to a file.

        Args:
            path: The file to write.
        """
        workbook = xlsxwriter.Workbook(str(path), {"constant_memory": True})
        self.write_problems(workbook.add_worksheet("problems"))
        self.write_summary(workbook.add_worksheet("summary"))
        workbook.close()

    def write_problems(self, sheet: xlsxwriter.worksheet.Worksheet) -> None:
        """Write the ``problems`` sheet, one row for each problem.

        Every value is written as text, so that a value starting with ``=`` is never
        a formula.

        Args:
            sheet: The sheet.
        """
        for column, (heading, width) in enumerate(zip(HEADINGS, WIDTHS, strict=True)):
            sheet.write_string(0, column, heading)
            sheet.set_column(column, column, width)
        sheet.freeze_panes(1, 0)
        for line, problem in enumerate(self.problems.itertuples(index=False), start=1):
            row, *texts = problem
            if not pandas.isna(row):
                sheet.write_number(line, 0, int(row))
            for column, text in enumerate(texts, start=1):
                if not pandas.isna(text):
                    sheet.write_string(line, column, str(text))
        sheet.autofilter(0, 0, max(len(self.problems), 1), len(HEADINGS) - 1)

    def write_summary(self, sheet: xlsxwriter.worksheet.Worksheet) -> None:
        """Write the ``summary`` sheet.

        Args:
            sheet: The sheet.
        """
        rows = self.problems["row"].dropna().nunique()
        lines: list[tuple[str, str | int]] = [
            ("Workbook", self.workbook_path.name),
            ("ghfdb version", __version__),
            ("Checked at (UTC)", datetime.now(UTC).isoformat(timespec="seconds")),
            ("Vocabulary releases", ", ".join(self.vocabularies.releases())),
            ("Children", self.children),
            ("Problems", len(self.problems)),
            ("Children with problems", int(rows)),
        ]
        for line, (label, value) in enumerate(lines):
            sheet.write_string(line, 0, label)
            if isinstance(value, int):
                sheet.write_number(line, 1, value)
            else:
                sheet.write_string(line, 1, value)
        if self.problems.empty:
            sheet.write_string(len(lines) + 1, 0, "No problem was found.")
        sheet.set_column(0, 0, 26)
        sheet.set_column(1, 1, 60)
