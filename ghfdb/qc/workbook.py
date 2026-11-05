"""The upload template workbook, read into a table of text."""

from pathlib import Path

import fastexcel
import pandas
from frictionless import Schema
from openpyxl.utils import get_column_letter

from ghfdb.fields import load_schema
from ghfdb.template import ROW_LABELS

SHEET = "data list"
SUFFIXES = {".xlsx", ".xlsm"}
HEADER_SEARCH_ROWS = 20
DESCRIPTION_LABELS = {label.casefold() for label in ROW_LABELS}


class CheckError(Exception):
    """Raised when a workbook cannot be checked, with the reason in the message."""


class UploadWorkbook:
    """The ``data list`` sheet of an upload template workbook.

    The sheet is read once, as text, and never changed. A formula is read as the
    value Excel last saved for it and is never calculated.

    Args:
        path: The workbook, an ``.xlsx`` or ``.xlsm`` file.
        schema: The fields the workbook is read against. Without one, the schema
            packaged with ghfdb.

    Attributes:
        path: The workbook.
        schema: The field schema the columns are matched to.
        frame: The whole sheet as text. Row ``i`` of the frame is Excel row
            ``i + 1``, whichever cell the sheet starts at.
        sheet_columns: For each column of ``frame``, its 0-based column in the sheet.
        header_row: The Excel row holding the field codes.
        first_data_row: The Excel row of the first row under the descriptions.
        columns: The position in ``frame`` of the first column for each field
            code found.
        unknown_columns: The header of each column that names no field, or the
            column letter of a column with no header that holds values.
        duplicate_columns: The code and header of each column that names a field
            an earlier column already names.

    Raises:
        CheckError: The path does not end ``.xlsx`` or ``.xlsm``, the file cannot
            be opened, it has no ``data list`` sheet, or the sheet has no header.
    """

    def __init__(self, path: Path, schema: Schema | None = None) -> None:
        self.path = path
        self.schema = load_schema() if schema is None else schema
        if path.suffix.casefold() not in SUFFIXES:
            raise CheckError(f"{path} is not an .xlsx or .xlsm workbook")
        self.frame, self.sheet_columns = self.read()
        self.header_row = self.find_header()
        self.first_data_row = self.find_first_data_row()
        self.columns: dict[str, int] = {}
        self.unknown_columns: list[str] = []
        self.duplicate_columns: list[tuple[str, str]] = []
        self.sort_columns()

    def read(self) -> tuple[pandas.DataFrame, list[int]]:
        """Read the ``data list`` sheet as text.

        Returns:
            The sheet, with Excel row 1 as its first row, and the sheet column of
            each of its columns.

        Raises:
            CheckError: The file cannot be opened or has no ``data list`` sheet.
        """
        try:
            sheet = fastexcel.read_excel(self.path).load_sheet_by_name(
                SHEET, header_row=None, skip_rows=0, dtypes="string"
            )
            frame = sheet.to_pandas()
            positions = [info.absolute_index for info in sheet.available_columns()]
        except fastexcel.SheetNotFoundError:
            raise CheckError(f"{self.path} has no sheet named {SHEET!r}") from None
        except fastexcel.FastExcelError as error:
            raise CheckError(f"{self.path} cannot be opened: {error}") from error
        return frame, positions

    def text(self, row: int, position: int) -> str:
        """Read one cell of the sheet as stripped text.

        Args:
            row: The cell's Excel row.
            position: The cell's column in ``frame``.

        Returns:
            The text without surrounding spaces, empty when the cell is empty.
        """
        value = self.frame.iat[row - 1, position]
        return value.strip() if isinstance(value, str) else ""

    def row_texts(self, row: int) -> list[str]:
        """Read a whole row of the sheet as stripped text.

        Args:
            row: The Excel row.

        Returns:
            The text of each cell of the row, empty for an empty cell.
        """
        return [self.text(row, position) for position in range(self.frame.shape[1])]

    def field_names(self) -> dict[str, str]:
        """List the names a column header may carry.

        Returns:
            The field code for each code, published column name and earlier column
            name. A code wins over a name another field also carries.
        """
        names: dict[str, str] = {}
        for field in self.schema.fields:
            names[field.name] = field.name
        for field in self.schema.fields:
            published = [
                field.custom["columnName"],
                *field.custom["earlierColumnNames"],
            ]
            for name in published:
                names.setdefault(name, field.name)
        return names

    def find_header(self) -> int:
        """Find the row holding the field codes.

        Returns:
            The Excel row of the first of the first 20 rows in which more than half
            of the filled cells after the first filled one name a field.

        Raises:
            CheckError: No row does.
        """
        names = self.field_names()
        for row in range(1, min(HEADER_SEARCH_ROWS, self.frame.shape[0]) + 1):
            filled = [text for text in self.row_texts(row) if text][1:]
            if filled and 2 * sum(text in names for text in filled) > len(filled):
                return row
        raise CheckError(f"{self.path} has no header row of field codes")

    def find_first_data_row(self) -> int:
        """Find the first row under the header that is not a description row.

        Returns:
            The Excel row. A row is a description row when its first filled cell is
            one of the description labels, whatever its case or surrounding spaces.
        """
        row = self.header_row + 1
        while row <= self.frame.shape[0]:
            filled = [text for text in self.row_texts(row) if text]
            if not filled or filled[0].casefold() not in DESCRIPTION_LABELS:
                break
            row += 1
        return row

    def sort_columns(self) -> None:
        """Match each column of the header to a field.

        The first filled column of the header is the row-label column and is matched
        to no field. A column with no header is unknown when a child holds a value
        in it.
        """
        names = self.field_names()
        headers = self.row_texts(self.header_row)
        label_column = next(i for i, header in enumerate(headers) if header)
        children = self.frame.iloc[self.first_data_row - 1 :]
        for position, header in enumerate(headers):
            if position == label_column:
                continue
            if not header:
                values = children.iloc[:, position].astype("string").str.strip()
                if values.fillna("").ne("").any():
                    self.unknown_columns.append(self.column_letter(position))
            elif header not in names:
                self.unknown_columns.append(header)
            elif names[header] in self.columns:
                self.duplicate_columns.append((names[header], header))
            else:
                self.columns[names[header]] = position

    def column_letter(self, position: int) -> str:
        """Name a column of the frame by its letter in the sheet.

        Args:
            position: The column's position in ``frame``.

        Returns:
            The column letter, such as ``C``.
        """
        return get_column_letter(self.sheet_columns[position] + 1)
