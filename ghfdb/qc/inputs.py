"""The fields the quality scheme scores, read once from a table of children."""

from collections.abc import Mapping

import numpy
import pandas
from pandas.api.types import infer_dtype

from ghfdb.fields.cells import parse_numbers


class Inputs:
    """The fields the scheme scores, read from a dataset the first time one is asked.

    A cell that holds a Python list holds several values, in any scored field. Every
    value is a row of its own under the child's index. Text is never split, where the
    check splits a cell by the field's separator (docs/adr/0009).

    Args:
        data: One row per child and one column per field, named by field code.
        uris: The URI of the concept of each term a vocabulary field accepts, by field.

    Attributes:
        index: The index of the children.
        data: The children.
        uris: The concept URI of each term, by field.
    """

    def __init__(
        self, data: pandas.DataFrame, uris: Mapping[str, Mapping[str, str]]
    ) -> None:
        self.index = data.index
        self.data = data
        self.uris = uris
        self.read_numbers: dict[str, pandas.Series] = {}
        self.read_concepts: dict[str, pandas.Series] = {}

    def text(self, field: str) -> pandas.Series:
        """Read a field as stripped text, one row for each value.

        Args:
            field: The field's code.

        Returns:
            The text of every value, empty for a field the data lacks.
        """
        if field not in self.data.columns:
            return pandas.Series(
                pandas.NA, index=self.index, dtype="string", name=field
            )
        column = self.data[field]
        if infer_dtype(column, skipna=True) == "mixed":
            column = column.explode()
        return column.astype("string").str.strip()

    def numbers(self, field: str) -> pandas.Series:
        """Read a number field.

        Args:
            field: The field.

        Returns:
            The number of every value as a float under its child's index, NaN where
            the cell is empty, is not a number or is infinite.
        """
        if field not in self.read_numbers:
            self.read_numbers[field] = parse_numbers(self.text(field))
        return self.read_numbers[field]

    def concepts(self, field: str) -> pandas.Series:
        """Read a vocabulary field as concepts.

        Args:
            field: The field, one whose concepts the scheme declares.

        Returns:
            The concept URI of every value under its child's index, empty where the
            cell is empty or holds a term the field does not allow.

        Raises:
            KeyError: The scheme declares no concept of the field.
        """
        if field not in self.read_concepts:
            text = self.text(field)
            self.read_concepts[field] = self.translate(text, self.uris[field])
        return self.read_concepts[field]

    @staticmethod
    def translate(values: pandas.Series, mapping: Mapping[str, str]) -> pandas.Series:
        """Replace each value by what the mapping gives it.

        Args:
            values: Text, with a row for each value.
            mapping: The replacement of each text it knows.

        Returns:
            The replacement of every value under its index, empty for a value that is
            empty or that the mapping does not know.
        """
        codes, found = pandas.factorize(values)
        # The last entry stays None: it is what the code -1 of an empty value takes.
        replaced = numpy.full(len(found) + 1, None, dtype=object)
        replaced[:-1] = pandas.Index(found).map(mapping).to_numpy(dtype=object)
        return pandas.Series(replaced[codes], index=values.index, dtype="string")

    def first(self, values: pandas.Series) -> pandas.Series:
        """Keep one value for each child: its first filled one.

        Args:
            values: A parsed field, with a row for each value.

        Returns:
            The value of each child in the order of the children, empty for a child
            with no filled value.
        """
        return values.groupby(level=0, sort=False).first().reindex(self.index)

    def any_value(self, holds: pandas.Series) -> numpy.ndarray:
        """Say for each child whether the test holds for any of its values.

        Args:
            holds: Whether the test holds, for every value.

        Returns:
            One boolean for each child in the order of the children.
        """
        found = holds.groupby(level=0, sort=False).any()
        return found.reindex(self.index, fill_value=False).to_numpy(dtype=bool)

    def every_value(self, holds: pandas.Series) -> numpy.ndarray:
        """Say for each child whether the test holds for all of its values.

        Args:
            holds: Whether the test holds, for every value.

        Returns:
            One boolean for each child in the order of the children.
        """
        found = holds.groupby(level=0, sort=False).all()
        return found.reindex(self.index, fill_value=False).to_numpy(dtype=bool)
