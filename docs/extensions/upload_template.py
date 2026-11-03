"""Publish the upload template while the documentation builds."""

import re
import warnings
from pathlib import Path
from typing import Any

from openpyxl import Workbook, load_workbook
from sphinx.application import Sphinx

import ghfdb
from extensions.field_reference import FieldReference
from ghfdb.template import UploadTemplate

PAGE_DIRECTORY = "upload-template"
DOWNLOAD_MARKER = re.compile(r"^\{upload-template-download\}$", re.MULTILINE)
CHANGES_MARKER = re.compile(r"^\{upload-template-changes\}$", re.MULTILINE)
HAND_MAINTAINED = (
    Path(__file__).parents[2] / "tests" / "sources" / "upload-template.xlsx"
)
PREVIOUS_LABELS = {"TC averaging method": "C48"}
NAME_ROW = 5
FIRST_DESCRIPTION_ROW = 2
LAST_DESCRIPTION_ROW = 8
FIRST_TERM_ROW = 3


def read_hand_maintained() -> Workbook:
    """Read the hand-maintained template, which is never written.

    Returns:
        The workbook. Excel's choice lists that openpyxl cannot read are left out.
    """
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore", message="Data Validation extension is not supported"
        )
        return load_workbook(HAND_MAINTAINED)


def collapse(value: Any) -> str:
    """Reduce a cell value to text that ignores whitespace and number formats.

    Args:
        value: The value of a cell.

    Returns:
        The value as text, with every run of whitespace, including non-breaking
        spaces, collapsed to one space and the ends stripped. An empty cell is ``""``.
    """
    return " ".join(("" if value is None else str(value)).split())


class TemplateChanges:
    """How the generated template differs from the hand-maintained one.

    Args:
        previous: The hand-maintained template.
        generated: The template generated from the field schema.
    """

    def __init__(self, previous: Workbook, generated: Workbook) -> None:
        self.previous = previous
        self.generated = generated

    @staticmethod
    def codes(workbook: Workbook) -> dict[str, int]:
        """Find the column of each field code on the ``data list`` sheet.

        Args:
            workbook: A template workbook.

        Returns:
            Each code in row 1, except the ``ID`` column, with its column number.
        """
        sheet = workbook["data list"]
        return {
            cell.value: cell.column
            for cell in sheet[1][1:]
            if cell.value not in (None, "")
        }

    def columns(self) -> tuple[list[str], list[str], bool]:
        """Compare the fields the two templates have.

        Returns:
            The codes only the generated template has, the codes only the
            hand-maintained one has, and whether the codes in both are in a
            different order.
        """
        before = list(self.codes(self.previous))
        after = list(self.codes(self.generated))
        added = [code for code in after if code not in before]
        removed = [code for code in before if code not in after]
        reordered = [c for c in before if c in after] != [
            c for c in after if c in before
        ]
        return added, removed, reordered

    def description_rows(self) -> list[tuple[str, str, str, str]]:
        """Find the description cells whose text differs.

        Returns:
            The code, the row label, the hand-maintained text and the generated
            text, for each field in both templates and each of rows 2 to 8 whose
            text differs once whitespace is collapsed.
        """
        before = self.previous["data list"]
        after = self.generated["data list"]
        before_columns = self.codes(self.previous)
        after_columns = self.codes(self.generated)
        rows = []
        for code in before_columns:
            if code not in after_columns:
                continue
            for row in range(FIRST_DESCRIPTION_ROW, LAST_DESCRIPTION_ROW + 1):
                was = collapse(before.cell(row, before_columns[code]).value)
                now = collapse(after.cell(row, after_columns[code]).value)
                if was != now:
                    rows.append((code, collapse(after.cell(row, 1).value), was, now))
        return rows

    def previous_terms(self) -> dict[str, list[str]]:
        """Read the terms of the hand-maintained template, by field code.

        Returns:
            The terms of each field that has a list, in the order they are written.

        Raises:
            ValueError: A column of terms matches no field by name or by
                ``PREVIOUS_LABELS``, naming its label.
        """
        data_list = self.previous["data list"]
        by_name = {
            collapse(data_list.cell(NAME_ROW, column).value).casefold(): code
            for code, column in self.codes(self.previous).items()
        }
        vocabulary = self.previous["controlled vocabulary"]
        terms: dict[str, list[str]] = {}
        for column in vocabulary.iter_cols(min_col=2, min_row=1):
            values = [collapse(cell.value) for cell in column[FIRST_TERM_ROW - 1 :]]
            values = [value for value in values if value]
            if not any("[" in value for value in values):
                continue
            label = collapse(column[0].value)
            code = PREVIOUS_LABELS.get(label) or by_name.get(label.casefold())
            if code is None:
                raise ValueError(f"No field matches the vocabulary column {label!r}")
            terms[code] = values
        return terms

    def generated_terms(self) -> dict[str, list[str]]:
        """Read the terms of the generated template, by field code.

        Returns:
            The terms of each field that has a list, in the order they are written.
        """
        vocabulary = self.generated["controlled vocabulary"]
        terms: dict[str, list[str]] = {}
        for column in vocabulary.iter_cols(min_col=2, min_row=1):
            code = column[0].value
            if code is None:
                continue
            values = [collapse(cell.value) for cell in column[FIRST_TERM_ROW - 1 :]]
            terms[code] = [value for value in values if value]
        return terms

    def choice_lists(
        self,
    ) -> tuple[list[tuple[str, list[str], list[str]]], list[str], list[str]]:
        """Compare the choice lists of the fields in both templates.

        Returns:
            The code, terms added and terms removed of each field with a list in
            both templates whose terms differ; the codes that gained a list; and the
            codes that lost one.
        """
        before = self.previous_terms()
        after = self.generated_terms()
        shared = [
            code
            for code in self.codes(self.previous)
            if code in self.codes(self.generated)
        ]
        changed, gained, lost = [], [], []
        for code in shared:
            if code in before and code in after:
                added = [term for term in after[code] if term not in before[code]]
                removed = [term for term in before[code] if term not in after[code]]
                if added or removed:
                    changed.append((code, added, removed))
            elif code in after:
                gained.append(code)
            elif code in before:
                lost.append(code)
        return changed, gained, lost

    def markdown(self) -> str:
        """Write the differences as Markdown.

        Returns:
            Three sections under ``###`` headings: columns, description rows and
            choice lists. A section with nothing to report says ``None.``.
        """
        added, removed, reordered = self.columns()
        changed, gained, lost = self.choice_lists()
        columns = []
        if added:
            columns.append(("Added", ", ".join(added)))
        if removed:
            columns.append(("Removed", ", ".join(removed)))
        if reordered:
            columns.append(("Order", "The fields are in a different order."))
        lists = [
            (code, "Terms added", "; ".join(terms))
            for code, terms, _ in changed
            if terms
        ]
        lists += [
            (code, "Terms removed", "; ".join(terms))
            for code, _, terms in changed
            if terms
        ]
        lists += [(code, "Gained a choice list", "") for code in gained]
        lists += [(code, "Lost its choice list", "") for code in lost]
        return "\n\n".join(
            [
                self.section("Columns", ("Change", "Fields"), columns),
                self.section(
                    "Description rows",
                    ("Field", "Row", "Hand-maintained", "Generated"),
                    self.description_rows(),
                ),
                self.section("Choice lists", ("Field", "Change", "Terms"), lists),
            ]
        )

    @staticmethod
    def section(
        heading: str, titles: tuple[str, ...], rows: list[tuple[str, ...]]
    ) -> str:
        """Write one heading and its table, or ``None.`` when there are no rows.

        Args:
            heading: The section's heading text.
            titles: The table's column titles.
            rows: The table rows, as plain text.

        Returns:
            The Markdown for the section.
        """
        if not rows:
            return f"### {heading}\n\nNone."
        table = [
            "| " + " | ".join(titles) + " |",
            "|" + "---|" * len(titles),
        ]
        table += [
            "| " + " | ".join(FieldReference.cell(text) for text in row) + " |"
            for row in rows
        ]
        return f"### {heading}\n\n" + "\n".join(table)


def template_name(version: str) -> str:
    """Name the published template after the package version that generates it.

    Args:
        version: The ghfdb version.

    Returns:
        The file name, such as ``ghfdb-upload-template-1.2.3.xlsx``.
    """
    return f"ghfdb-upload-template-{version}.xlsx"


def write_template(template: UploadTemplate, source_directory: Path) -> Path:
    """Write the template beside the page that links it, replacing an earlier build's.

    Args:
        template: The template to write.
        source_directory: The documentation source directory.

    Returns:
        The path of the written file.

    Raises:
        TemplateError: The template cannot be generated. The build fails.
    """
    path = source_directory / PAGE_DIRECTORY / template_name(template.version)
    path.parent.mkdir(parents=True, exist_ok=True)
    template.write(path, replace=True)
    return path


def replace_markers(text: str, name: str, changes: TemplateChanges) -> str:
    """Replace each marker line in a page with the Markdown it stands for.

    Args:
        text: The raw source of a page.
        name: The file name of the published template.
        changes: How the generated template differs from the hand-maintained one.

    Returns:
        The page with the ``{upload-template-download}`` and
        ``{upload-template-changes}`` lines replaced.
    """
    text = DOWNLOAD_MARKER.sub(lambda _: f"{{download}}`{name} <{name}>`", text)
    return CHANGES_MARKER.sub(lambda _: changes.markdown(), text)


def builder_inited(app: Sphinx) -> None:
    """Write the template where the page links to it."""
    write_template(UploadTemplate(), Path(app.srcdir))


def source_read(app: Sphinx, docname: str, source: list[str]) -> None:
    """Fill in the upload template markers of a page being read."""
    if "{upload-template-" in source[0]:
        changes = TemplateChanges(read_hand_maintained(), UploadTemplate().workbook())
        source[0] = replace_markers(
            source[0], template_name(ghfdb.__version__), changes
        )


def setup(app: Sphinx) -> dict[str, Any]:
    """Register the extension's two handlers.

    Args:
        app: The Sphinx application.

    Returns:
        The extension's metadata.
    """
    app.connect("builder-inited", builder_inited)
    app.connect("source-read", source_read)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
