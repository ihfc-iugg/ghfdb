"""The check of a table of children against the field schema."""

import difflib
import math
from collections.abc import Iterable
from enum import StrEnum

import pandas
from frictionless import Field, Schema

PROBLEM_COLUMNS = ["row", "code", "column_name", "kind", "value", "suggestion"]
CLOSE_ENOUGH = 0.8


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
        found = []
        for order, field in enumerate(self.schema.fields):
            if field.name in self.data.columns:
                found.append(self.field_problems(order, field))
            else:
                found.append(self.absent_problems(order, field))
        frame = pandas.concat(
            [self.typed(pandas.DataFrame(columns=[*PROBLEM_COLUMNS, "order"])), *found]
        )
        frame = frame.sort_values(["row", "order"], kind="stable", na_position="first")
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
        self,
        order: int,
        field: Field,
        kind: Kind,
        values: pandas.Series,
        suggestions: dict[str, str] | None = None,
    ) -> pandas.DataFrame:
        """Build the problem lines for the cells of one field that share a kind.

        Args:
            order: The field's place in the schema.
            field: The field.
            kind: The kind of problem.
            values: The offending cells, indexed by row.
            suggestions: The term to offer for each value, where there is one.

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
                    "suggestion": values.map(suggestions or {}).to_numpy(),
                    "order": order,
                }
            )
        )

    @staticmethod
    def is_required(field: Field) -> bool:
        """Say whether an empty cell in a field is a problem.

        Args:
            field: The field.

        Returns:
            True for a mandatory field in both the borehole and the site domain.
        """
        return field.custom["obligation"] == "M" and set(field.custom["domain"]) == {
            "B",
            "S",
        }

    def absent_problems(self, order: int, field: Field) -> pandas.DataFrame:
        """Report a field the data has no column for.

        Args:
            order: The field's place in the schema.
            field: The field.

        Returns:
            One ``no column`` line without a row, and for a required field a
            ``missing`` line for every child.
        """
        none = pandas.Series([None], index=pandas.Index([None]), dtype="string")
        found = [self.lines(order, field, Kind.NO_COLUMN, none)]
        if self.is_required(field):
            nothing = pandas.Series(pandas.NA, index=self.data.index, dtype="string")
            found.append(self.lines(order, field, Kind.MISSING, nothing))
        return pandas.concat(found)

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
        values = self.each_value(field, filled)
        if "pattern" in constraints:
            bad = values[~values.str.fullmatch(constraints["pattern"])]
            found.append(self.lines(order, field, Kind.WRONG_TYPE, bad))
        if "maxLength" in constraints:
            long = filled[filled.str.len() > constraints["maxLength"]]
            found.append(self.lines(order, field, Kind.OUT_OF_RANGE, long))
        if "enum" in constraints:
            unknown = values[~values.isin(constraints["enum"])]
            suggestions = self.suggestions(field, unknown.unique())
            found.append(
                self.lines(order, field, Kind.NOT_IN_VOCABULARY, unknown, suggestions)
            )
        return (
            pandas.concat(found)
            if found
            else self.lines(order, field, Kind.MISSING, filled[:0])
        )

    @staticmethod
    def each_value(field: Field, filled: pandas.Series) -> pandas.Series:
        """Split the cells of a field that holds several values in a cell.

        Only a field with allowed values or a pattern is split. Each value keeps the
        row of its cell.

        Args:
            field: The field.
            filled: The cells that are not empty.

        Returns:
            One entry for each value, without surrounding spaces. The cells
            themselves for a field that takes one value.
        """
        separator = field.custom["separator"]
        if not separator or not {"enum", "pattern"} & set(field.constraints):
            return filled
        values = filled.str.split(separator, regex=False).explode().str.strip()
        return values[values != ""].astype("string")

    @staticmethod
    def normalised(text: str) -> str:
        """Reduce a value or a term to what is compared when looking for a likeness.

        Args:
            text: A cell's value or a vocabulary term.

        Returns:
            The text without square brackets or surrounding spaces, in lower case.
        """
        return text.strip().strip("[]").strip().casefold()

    def suggestions(self, field: Field, values: Iterable[str]) -> dict[str, str]:
        """Find the vocabulary term each value is closest to.

        A value that is a term once brackets, spaces and case are ignored gets that
        term. Otherwise it gets the closest term that is at least 80% alike.

        Args:
            field: A field with allowed values.
            values: The distinct values that are not allowed.

        Returns:
            The term for each value that has one close enough.
        """
        terms: dict[str, str] = {}
        for term in field.constraints["enum"]:
            terms.setdefault(self.normalised(term), term)
        found = {}
        for value in values:
            key = self.normalised(value)
            if key not in terms:
                close = difflib.get_close_matches(
                    key, list(terms), n=1, cutoff=CLOSE_ENOUGH
                )
                if not close:
                    continue
                key = close[0]
            found[value] = terms[key]
        return found

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
