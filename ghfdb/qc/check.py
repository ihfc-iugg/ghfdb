"""The check of a table of children against the field schema."""

import math
from enum import StrEnum

import pandas
from frictionless import Field, Schema

PROBLEM_COLUMNS = ["row", "code", "column_name", "kind", "value", "suggestion"]


class Kind(StrEnum):
    """The kinds of problem a check finds."""

    MISSING = "missing"
    WRONG_TYPE = "wrong type"
    OUT_OF_RANGE = "out of range"
    NOT_IN_VOCABULARY = "not in vocabulary"
    UNKNOWN_COLUMN = "unknown column"
    NO_COLUMN = "no column"
    DUPLICATE_COLUMN = "duplicate column"


class DatasetCheck:
    """Check the children of a dataset against a field schema.

    Args:
        data: One row per child and one text column per field, named by field code.
            The index is the row reported with each problem.
        schema: The fields to check against.

    Attributes:
        data: The children.
        schema: The fields.
    """

    def __init__(self, data: pandas.DataFrame, schema: Schema) -> None:
        self.data = data
        self.schema = schema

    def problems(self) -> pandas.DataFrame:
        """Find what is wrong with the children.

        Returns:
            One line for each problem, with the columns ``row``, ``code``,
            ``column_name``, ``kind``, ``value`` and ``suggestion``, ordered by row
            and then by the field's place in the schema.
        """
        found = [
            self.field_problems(order, field)
            for order, field in enumerate(self.schema.fields)
            if field.name in self.data.columns
        ]
        frame = pandas.concat(
            [self.typed(pandas.DataFrame(columns=[*PROBLEM_COLUMNS, "order"])), *found]
        )
        frame = frame.sort_values(["row", "order"], kind="stable")
        return frame[PROBLEM_COLUMNS].reset_index(drop=True)

    @staticmethod
    def typed(frame: pandas.DataFrame) -> pandas.DataFrame:
        """Give the columns of a problem table their types.

        Args:
            frame: A table with the problem columns and ``order``.

        Returns:
            The table, its row a nullable integer and the rest text.
        """
        text = [column for column in PROBLEM_COLUMNS if column != "row"]
        return frame.astype(
            {"row": "Int64", "order": "int64"} | dict.fromkeys(text, "string")
        )

    def lines(
        self, order: int, field: Field, kind: Kind, values: pandas.Series
    ) -> pandas.DataFrame:
        """Build the problem lines for the cells of one field that share a kind.

        Args:
            order: The field's place in the schema.
            field: The field.
            kind: The kind of problem.
            values: The offending cells, indexed by row.

        Returns:
            The problem lines.
        """
        return self.typed(
            pandas.DataFrame(
                {
                    "row": values.index,
                    "code": field.name,
                    "column_name": field.custom["columnName"],
                    "kind": str(kind),
                    "value": values.to_numpy(),
                    "suggestion": None,
                    "order": order,
                }
            )
        )

    def field_problems(self, order: int, field: Field) -> pandas.DataFrame:
        """Check one field's column.

        Args:
            order: The field's place in the schema.
            field: The field.

        Returns:
            The problem lines for the column.
        """
        column = self.data[field.name].astype("string")
        blank = column.str.strip().fillna("").eq("")
        filled = column[~blank]
        constraints = field.constraints
        found = []
        if field.custom["obligation"] == "M" and set(field.custom["domain"]) == {
            "B",
            "S",
        }:
            found.append(self.lines(order, field, Kind.MISSING, column[blank]))
        if field.type in ("number", "integer"):
            found += self.number_problems(order, field, filled)
        if "pattern" in constraints:
            bad = filled[~filled.str.fullmatch(constraints["pattern"])]
            found.append(self.lines(order, field, Kind.WRONG_TYPE, bad))
        if "maxLength" in constraints:
            long = filled[filled.str.len() > constraints["maxLength"]]
            found.append(self.lines(order, field, Kind.OUT_OF_RANGE, long))
        if "enum" in constraints:
            unknown = filled[~filled.isin(constraints["enum"])]
            found.append(self.lines(order, field, Kind.NOT_IN_VOCABULARY, unknown))
        return (
            pandas.concat(found)
            if found
            else self.lines(order, field, Kind.MISSING, filled[:0])
        )

    def number_problems(
        self, order: int, field: Field, filled: pandas.Series
    ) -> list[pandas.DataFrame]:
        """Check the filled cells of a number or whole-number field.

        Args:
            order: The field's place in the schema.
            field: The field.
            filled: The cells that are not empty.

        Returns:
            Lines for the cells that are not numbers and for the numbers out of range.
        """
        numbers = pandas.to_numeric(filled.str.strip(), errors="coerce").astype(
            "float64"
        )
        wrong = numbers.isna() | numbers.abs().eq(math.inf)
        if field.type == "integer":
            wrong |= numbers != numbers.round()
        constraints = field.constraints
        outside = pandas.Series(False, index=numbers.index)
        if "minimum" in constraints:
            outside |= numbers < constraints["minimum"]
        if "maximum" in constraints:
            outside |= numbers > constraints["maximum"]
        return [
            self.lines(order, field, Kind.WRONG_TYPE, filled[wrong]),
            self.lines(order, field, Kind.OUT_OF_RANGE, filled[outside & ~wrong]),
        ]
