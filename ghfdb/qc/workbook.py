"""The upload template workbook, read into a table of text."""

import re
import zipfile
from pathlib import Path
from xml.sax.saxutils import unescape as xml_unescape

import fastexcel
import pandas
from frictionless import Schema
from openpyxl.utils import column_index_from_string, get_column_letter

from ghfdb.fields import load_schema
from ghfdb.qc.check import PROBLEM_COLUMNS, Kind
from ghfdb.template import ROW_LABELS

SHEET = "data list"
SUFFIXES = {".xlsx", ".xlsm"}
HEADER_SEARCH_ROWS = 20
DESCRIPTION_LABELS = {label.casefold() for label in ROW_LABELS}
ENTITIES = {"&quot;": '"', "&apos;": "'"}
ATTRIBUTE = re.compile(rb"""([\w:.-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')""")
CELL_REFERENCE = re.compile(rb"""\br\s*=\s*["']([A-Z]+)([0-9]+)["']""")
ERROR_CELL = re.compile(
    rb"""<c\s(?=[^>]*\bt\s*=\s*["']e["'])([^>]*)>\s*"""
    rb"""(?:<f\b[^>]*/>|<f\b[^>]*>[^<]*</f>)?\s*<v>([^<]*)</v>"""
)


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
            table = sheet.to_arrow()
            positions = [info.absolute_index for info in sheet.available_columns()]
        except fastexcel.SheetNotFoundError:
            raise CheckError(f"{self.path} has no sheet named {SHEET!r}") from None
        except fastexcel.FastExcelError as error:
            raise CheckError(f"{self.path} cannot be opened: {error}") from error
        # A column with no cell filled is dropped before pandas sees it, so a stray
        # value far to the right of the fields costs nothing. The error-cell scan
        # restores any column whose only cells hold Excel errors.
        errors = self.error_values()
        kept = [
            index
            for index, column in enumerate(table.columns)
            if column.null_count < table.num_rows or positions[index] in errors
        ]
        frame = table.select(kept).to_pandas()
        frame.columns = pandas.RangeIndex(len(kept))
        positions = [positions[index] for index in kept]
        self.put_error_values(frame, positions, errors)
        return frame, positions

    def error_values(self) -> dict[int, dict[int, str]]:
        """Find the Excel error values of the sheet.

        The reader gives a cell holding an error such as ``#N/A`` as empty. The
        sheet's XML is searched as bytes for those cells, so that no entity in an
        untrusted file is ever expanded.

        Returns:
            The error text of each error cell, by sheet column and then Excel row,
            both counted as the reader counts them: columns from 0, rows from 1.

        Raises:
            CheckError: The file is not a workbook archive or has no ``data list``
                sheet part.
        """
        try:
            with zipfile.ZipFile(self.path) as archive:
                sheet_xml = archive.read(self.sheet_part(archive))
        except (zipfile.BadZipFile, KeyError, OSError) as error:
            raise CheckError(f"{self.path} cannot be opened: {error}") from error
        errors: dict[int, dict[int, str]] = {}
        if b'"e"' not in sheet_xml and b"'e'" not in sheet_xml:
            # No cell has the error type, whatever the spacing around its "=". A plain
            # search takes a quarter of the time of the full pattern on a large sheet.
            return errors
        for cell in ERROR_CELL.finditer(sheet_xml):
            reference = CELL_REFERENCE.search(cell.group(1))
            if reference is None:
                continue
            column = column_index_from_string(reference.group(1).decode()) - 1
            row = int(reference.group(2))
            errors.setdefault(column, {})[row] = self.unescape(cell.group(2).decode())
        return errors

    @staticmethod
    def put_error_values(
        frame: pandas.DataFrame,
        positions: list[int],
        errors: dict[int, dict[int, str]],
    ) -> None:
        """Write the Excel error values of the sheet into its frame.

        Args:
            frame: The sheet as read, changed in place.
            positions: The sheet column of each column of ``frame``.
            errors: The error text of each error cell, from ``error_values``.
        """
        for position, column in enumerate(positions):
            for row, text in errors.get(column, {}).items():
                if row <= frame.shape[0]:
                    frame.iat[row - 1, position] = text

    @staticmethod
    def unescape(text: str) -> str:
        """Replace the XML entities of a text with the characters they stand for.

        Args:
            text: Text taken from the sheet's XML.

        Returns:
            The text with every entity replaced.
        """
        return xml_unescape(text, ENTITIES)

    @staticmethod
    def attributes(tag: bytes) -> dict[str, str]:
        """Read the attributes of one XML start tag.

        Args:
            tag: The tag, such as ``<sheet name="data list" r:id="rId2"/>``.

        Returns:
            The attribute values by name, with XML entities unescaped.
        """
        return {
            match.group(1).decode(): UploadWorkbook.unescape(
                (match.group(2) or match.group(3)).decode()
            )
            for match in ATTRIBUTE.finditer(tag)
        }

    def sheet_part(self, archive: zipfile.ZipFile) -> str:
        """Find the part of the archive holding the ``data list`` sheet.

        The part is found from the sheet's relationship id, never from the sheet's
        number or position.

        Args:
            archive: The workbook as a zip archive.

        Returns:
            The name of the part.

        Raises:
            KeyError: The workbook names no such sheet or no such relationship.
        """
        sheets = (
            self.attributes(tag)
            for tag in re.findall(rb"<sheet\b[^>]*>", archive.read("xl/workbook.xml"))
        )
        sheet = next((tag for tag in sheets if tag.get("name") == SHEET), None)
        if sheet is None:
            raise KeyError(SHEET)
        identifier = next(v for k, v in sheet.items() if k.split(":")[-1] == "id")
        rels = archive.read("xl/_rels/workbook.xml.rels")
        for tag in re.findall(rb"<Relationship\b[^>]*>", rels):
            relationship = self.attributes(tag)
            if relationship.get("Id") == identifier:
                target = relationship["Target"]
                return target[1:] if target.startswith("/") else f"xl/{target}"
        raise KeyError(identifier)

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

        Raises:
            CheckError: The first filled column of the header is a field code that
                no other column names, so the ID column in front of the fields is
                missing.
        """
        names = self.field_names()
        headers = self.row_texts(self.header_row)
        label_column = next(i for i, header in enumerate(headers) if header)
        codes = {field.name for field in self.schema.fields}
        label = headers[label_column]
        others = {names.get(header) for header in headers[label_column + 1 :]}
        if label in codes and label not in others:
            raise CheckError(
                f"{self.path} has no ID column in front of the field codes of its "
                "header row"
            )
        blank = [
            position
            for position, header in enumerate(headers)
            if not header and position != label_column
        ]
        cells = self.frame.iloc[self.first_data_row - 1 :, blank].stack()
        holding = set(
            cells[cells.astype("string").str.strip().ne("")].index.get_level_values(1)
        )
        for position, header in enumerate(headers):
            if position == label_column:
                continue
            if not header:
                if self.frame.columns[position] in holding:
                    self.unknown_columns.append(self.column_letter(position))
            elif header not in names:
                self.unknown_columns.append(header)
            elif names[header] in self.columns:
                self.duplicate_columns.append((names[header], header))
            else:
                self.columns[names[header]] = position

    def data(self) -> pandas.DataFrame:
        """Build the table of the children.

        Returns:
            One row per child and one text column per field found, named by field
            code. The index, named ``row``, is the child's Excel row. A cell of
            spaces only is missing, and a row with every field missing is no
            child and is left out.
        """
        positions = list(self.columns.values())
        children = self.frame.iloc[self.first_data_row - 1 :, positions].copy()
        children.columns = pandas.Index(self.columns)
        children.index = pandas.Index(children.index + 1, name="row")
        for code in children.columns:
            column = children[code]
            children[code] = column.mask(column.str.strip().eq(""))
        return children.dropna(how="all")

    def column_problems(self) -> pandas.DataFrame:
        """List the problems that belong to the workbook's layout.

        Returns:
            One line for each unknown column and each column that repeats a field,
            with the columns ``row``, ``code``, ``column_name``, ``kind``,
            ``value`` and ``suggestion``. The row is always empty. The first column
            for a field is the one ``data`` uses.
        """
        unknown = [
            {"column_name": header, "kind": Kind.UNKNOWN_COLUMN}
            for header in self.unknown_columns
        ]
        duplicate = [
            {"code": code, "column_name": header, "kind": Kind.DUPLICATE_COLUMN}
            for code, header in self.duplicate_columns
        ]
        problems = pandas.DataFrame([*unknown, *duplicate], columns=PROBLEM_COLUMNS)
        return problems.astype(
            {"row": "Int64"} | dict.fromkeys(PROBLEM_COLUMNS[1:], "string")
        )

    def column_letter(self, position: int) -> str:
        """Name a column of the frame by its letter in the sheet.

        Args:
            position: The column's position in ``frame``.

        Returns:
            The column letter, such as ``C``.
        """
        return get_column_letter(self.sheet_columns[position] + 1)
