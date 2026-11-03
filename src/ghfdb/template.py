"""The upload template: the workbook a contributor fills in, built from the schema."""

from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from ghfdb.fields import FieldSchema

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
        schema: The fields to build the template from. Without one, the schema
            packaged with ghfdb.

    Attributes:
        schema: The field schema the template is built from.
    """

    def __init__(self, schema: FieldSchema | None = None) -> None:
        self.schema = FieldSchema.load() if schema is None else schema

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
        workbook.create_sheet("controlled vocabulary")
        self.fill_data_list(data_list)
        return workbook

    def fill_data_list(self, sheet: Worksheet) -> None:
        """Write the header row and the row labels of the ``data list`` sheet.

        Args:
            sheet: The sheet to write to.
        """
        sheet["A1"] = "ID"
        for row, label in enumerate(ROW_LABELS, start=2):
            sheet.cell(row, 1, label)
        for index, field in enumerate(self.schema):
            sheet.cell(1, index + 2, field.code)
        for cell in sheet[1]:
            cell.font = Font(bold=True)
        sheet.freeze_panes = "B9"

    @staticmethod
    def column_letter(index: int) -> str:
        """Name the column a field sits in on ``data list``.

        Args:
            index: The field's position in the schema, from 0.

        Returns:
            The column letter. The first field sits in ``B``, after ``ID``.
        """
        return get_column_letter(index + 2)
