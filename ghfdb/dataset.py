"""The data of a set of children, held as a table."""

from collections.abc import Sequence
from pathlib import Path

import pandas
from frictionless import Schema

from ghfdb.fields import Vocabularies, load_schema
from ghfdb.qc.check import DatasetCheck
from ghfdb.qc.rules import RULES, Rule
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

    def check(
        self,
        schema: Schema | None = None,
        rules: Sequence[Rule] = RULES,
        vocabularies: Vocabularies | None = None,
    ) -> pandas.DataFrame:
        """Find what is wrong with the children.

        Args:
            schema: The fields to check against. Without one, the schema packaged
                with ghfdb.
            rules: The cross-field rules to apply after the field check. Without
                them, all the rules ghfdb declares; an empty sequence applies none.
            vocabularies: Where the allowed values of the rules' concepts come from.
                Without it, the vocabularies in the user's cache, downloaded when
                missing.

        Returns:
            One line for each problem, with the columns ``row``, ``code``,
            ``column_name``, ``kind``, ``value``, ``suggestion``, ``rule`` and
            ``related``. ``rule`` and ``related`` are set for a problem of kind
            ``rule`` only: ``rule`` is the rule's identifier and ``related`` the
            field that made the rule apply, with the value found, such as
            ``P12 explo_method [Drilling]``.

        Raises:
            MissingSchemeError: A concept a rule names is not an allowed value of
                its field.
        """
        schema = load_schema() if schema is None else schema
        return DatasetCheck(self.data, schema, rules, vocabularies).problems()
