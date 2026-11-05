"""The data of a set of children, held as a table."""

from pathlib import Path

import pandas
from frictionless import Schema

from ghfdb.fields import load_schema
from ghfdb.qc.check import DatasetCheck
from ghfdb.qc.workbook import UploadWorkbook


class Dataset:
    """The children of a heat-flow dataset, one row each.

    Args:
        data: The children: one row per child and one column per field, named by
            field code.

    Attributes:
        data: The table of children, an ordinary pandas DataFrame to work on with
            all of pandas.
    """

    def __init__(self, data: pandas.DataFrame) -> None:
        self.data = data

    @classmethod
    def from_workbook(cls, path: Path, schema: Schema | None = None) -> "Dataset":
        """Read the children from an upload template workbook.

        Args:
            path: The workbook, an ``.xlsx`` or ``.xlsm`` file.
            schema: The fields to read the workbook against. Without one, the
                schema packaged with ghfdb.

        Returns:
            A dataset whose ``data`` is indexed by the Excel row of each child.

        Raises:
            CheckError: The workbook cannot be read.
        """
        return cls(UploadWorkbook(path, schema).data())

    def check(self, schema: Schema | None = None) -> pandas.DataFrame:
        """Find what is wrong with the children.

        Args:
            schema: The fields to check against. Without one, the schema packaged
                with ghfdb.

        Returns:
            One line for each problem, with the columns ``row``, ``code``,
            ``column_name``, ``kind``, ``value`` and ``suggestion``.
        """
        schema = load_schema() if schema is None else schema
        return DatasetCheck(self.data, schema).problems()
