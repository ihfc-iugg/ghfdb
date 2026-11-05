"""The data of a set of children, held as a table."""

from pathlib import Path

import pandas
from frictionless import Schema

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
