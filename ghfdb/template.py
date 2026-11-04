"""The upload template: the workbook a contributor fills in, built from the schema."""

from pathlib import Path

from frictionless import Field, Schema
from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.worksheet import Worksheet

from ghfdb import __version__
from ghfdb.fields import load_schema

NONE = "-"
VOCABULARIES = "https://w3id.org/ihfc-iugg/vocabularies"
FIELD_REFERENCE = "https://ihfc-iugg.github.io/ghfdb/reference/fields/index.html"
LAST_ROW = 1048576
FIRST_DATA_ROW = 9
FIRST_TERM_ROW = 3


class TemplateError(ValueError):
    """A field the template cannot be written for, named in the message."""


ROW_LABELS = (
    "Obligation",
    "Domain",
    "Quality Relevance",
    "Name",
    "Short Name",
    "Unit",
    "Allowed range of values",
)


class UploadTemplate:
    """The upload template, generated from a field schema.

    Args:
        schema: The fields to build the template from, as a Frictionless Table
            Schema. Without one, the schema packaged with ghfdb.

    Attributes:
        schema: The field schema the template is built from.
        version: The ghfdb version that generates the template.
    """

    def __init__(self, schema: Schema | None = None) -> None:
        self.schema = load_schema() if schema is None else schema
        self.version = __version__

    def workbook(self) -> Workbook:
        """Build the template workbook.

        Returns:
            A workbook with the sheets ``readme``, ``data list`` and
            ``controlled vocabulary``, in that order.
        """
        workbook = Workbook()
        readme = workbook.active
        assert readme is not None
        readme.title = "readme"
        data_list = workbook.create_sheet("data list")
        vocabulary = workbook.create_sheet("controlled vocabulary")
        self.fill_readme(readme)
        self.fill_data_list(data_list)
        self.fill_vocabulary(vocabulary, data_list)
        return workbook

    def write(self, path: Path, replace: bool = False) -> None:
        """Write the template to a file.

        The workbook is built before the file is opened, so a failure to build it
        leaves no file behind.

        Args:
            path: Where to write the template.
            replace: Replace the file when it exists. Without it, an existing file
                is left untouched.

        Raises:
            FileExistsError: The file exists and ``replace`` is false.
            TemplateError: A field names a controlled vocabulary but has no
                allowed values.
        """
        workbook = self.workbook()
        try:
            with open(path, "wb" if replace else "xb") as file:
                workbook.save(file)
        except FileExistsError:
            raise FileExistsError(
                f"{path} already exists; pass replace=True to replace it"
            ) from None

    def fill_readme(self, sheet: Worksheet) -> None:
        """Write what the workbook is, where it came from and how to fill it in.

        Args:
            sheet: The ``readme`` sheet to write to.
        """
        lines = (
            "Upload template for the Global Heat Flow Database.",
            f"Package version: {self.version}",
            f"Vocabularies: {VOCABULARIES}",
            f"Field reference: {FIELD_REFERENCE}",
            "Enter your data on the 'data list' sheet, one row per record from row 9.",
            "Cells with a choice list offer the allowed terms and accept any value.",
        )
        for row, line in enumerate(lines, start=1):
            sheet.cell(row, 1, line)

    def fill_data_list(self, sheet: Worksheet) -> None:
        """Write the header row and the row labels of the ``data list`` sheet.

        Args:
            sheet: The sheet to write to.
        """
        sheet["A1"] = "ID"
        for row, label in enumerate(ROW_LABELS, start=2):
            sheet.cell(row, 1, label)
        for index, field in enumerate(self.schema.fields):
            sheet.cell(1, index + 2, field.name)
            for row, value in enumerate(self.describe(field), start=2):
                sheet.cell(row, index + 2, value)
        for cell in sheet[1]:
            cell.font = Font(bold=True)
        sheet.freeze_panes = "B9"

    def fill_vocabulary(self, vocabulary: Worksheet, data_list: Worksheet) -> None:
        """Write the terms of every field with allowed values, and a choice list each.

        Each field's terms sit in the column its field has on ``data list``. The
        choice list accepts any value, so a contributor can type a term that is
        not offered.

        Args:
            vocabulary: The ``controlled vocabulary`` sheet to write to.
            data_list: The ``data list`` sheet to add the choice lists to.

        Raises:
            TemplateError: A field names a controlled vocabulary but has no
                allowed values.
        """
        vocabulary["A1"] = "Field code"
        vocabulary["A2"] = "Name"
        for index, field in enumerate(self.schema.fields):
            terms: list[str] = field.constraints.get("enum", [])
            if not terms:
                if field.custom["vocabulary"] is not None:
                    raise TemplateError(
                        f"Field {field.name} names a controlled vocabulary "
                        "but has no allowed values"
                    )
                continue
            letter = self.column_letter(index)
            vocabulary[f"{letter}1"] = field.name
            vocabulary[f"{letter}2"] = field.title
            for row, term in enumerate(terms, start=FIRST_TERM_ROW):
                vocabulary[f"{letter}{row}"] = term
            last = FIRST_TERM_ROW + len(terms) - 1
            cells = f"${letter}${FIRST_TERM_ROW}:${letter}${last}"
            choices = DataValidation(
                type="list",
                formula1=f"'controlled vocabulary'!{cells}",
                allow_blank=True,
                showErrorMessage=False,
            )
            choices.add(f"{letter}{FIRST_DATA_ROW}:{letter}{LAST_ROW}")
            data_list.add_data_validation(choices)

    @staticmethod
    def describe(field: Field) -> tuple[str, ...]:
        """List the description rows of a field.

        Args:
            field: The field to describe.

        Returns:
            The seven strings of rows 2 to 8, in row order. ``-`` stands for a
            value the field does not have.
        """
        return (
            field.custom["obligation"] or NONE,
            ",".join(field.custom["domain"]) or NONE,
            field.custom["qualityRelevance"] or NONE,
            field.title or NONE,
            field.custom["columnName"],
            field.custom["unit"] or NONE,
            UploadTemplate.allowed_range(field),
        )

    @staticmethod
    def allowed_range(field: Field) -> str:
        """Write the allowed range of values of a field.

        Args:
            field: The field to describe.

        Returns:
            The minimum and maximum joined by an en dash when the field has both,
            else its value format, else ``-``. A field with allowed values has a
            choice list instead, so it also shows ``-``.
        """
        if field.constraints.get("enum"):
            return NONE
        minimum = field.constraints.get("minimum")
        maximum = field.constraints.get("maximum")
        if minimum is not None and maximum is not None:
            places = field.custom["decimalPlaces"] or 0
            return f"{minimum:,.{places}f} \u2013 {maximum:,.{places}f}"
        return field.custom["valueFormat"] or NONE

    @staticmethod
    def column_letter(index: int) -> str:
        """Name the column a field sits in on ``data list``.

        Args:
            index: The field's position in the schema, from 0.

        Returns:
            The column letter. The first field sits in ``B``, after ``ID``.
        """
        return get_column_letter(index + 2)
