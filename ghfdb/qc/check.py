"""The check of a table of children against the field schema."""

import difflib
from collections.abc import Iterable, Sequence
from enum import StrEnum

import pandas
from frictionless import Field, Schema

from ghfdb.fields.cells import parse_numbers, terms_by_name
from ghfdb.qc.rules import Condition, Rule
from ghfdb.vocabularies import MissingSchemeError, Vocabularies

PROBLEM_COLUMNS = [
    "row",
    "code",
    "column_name",
    "kind",
    "value",
    "suggestion",
    "rule",
    "related",
]
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
    RULE = "rule"


class DatasetCheck:
    """Check the children of a dataset against a field schema.

    Args:
        data: One row per child and one text column per field, named by field code.
            The index is the row reported with each problem.
        schema: The fields to check against.

    Attributes:
        data: The children.
        schema: The fields.
        rules: The cross-field rules applied after the field check.
        terms: The term of every concept the rules name, by field code and concept
            name.
    """

    def __init__(
        self,
        data: pandas.DataFrame,
        schema: Schema,
        rules: Sequence[Rule] = (),
        vocabularies: Vocabularies | None = None,
    ) -> None:
        """Remember what to check and turn the rules' concepts into terms.

        Args:
            data: One row per child and one text column per field, named by field code.
            schema: The fields to check against.
            rules: The cross-field rules to apply.
            vocabularies: Where the allowed values of the concepts come from. Without
                it, the vocabularies in the user's cache, downloaded when missing.

        Raises:
            MissingSchemeError: A concept a rule or its example names is not an allowed
                value of its field. The message names the rule and the concept.
        """
        self.data = data
        self.schema = schema
        self.rules = tuple(rules)
        self.terms = self.resolve(vocabularies)

    def resolve(self, vocabularies: Vocabularies | None) -> dict[tuple[str, str], str]:
        """Turn the concepts of the rules into the terms their fields accept.

        Args:
            vocabularies: Where the allowed values come from.

        Returns:
            The term of each concept, by field code and concept name.

        Raises:
            MissingSchemeError: A concept is not an allowed value of its field, or the
                field is not in the schema.
        """
        if not self.rules:
            return {}
        files = Vocabularies() if vocabularies is None else vocabularies
        allowed: dict[str, dict[str, str]] = {}
        terms = {}
        for rule in self.rules:
            for code, name in rule.concepts():
                if code not in allowed:
                    allowed[code] = self.names(code, files)
                if name not in allowed[code]:
                    raise MissingSchemeError(
                        f"{rule.identifier}: {name} is not an allowed value of {code}"
                    )
                terms[code, name] = allowed[code][name]
        return terms

    def names(self, code: str, vocabularies: Vocabularies) -> dict[str, str]:
        """Map the local name of each allowed value of a field to its term.

        Args:
            code: The field's code.
            vocabularies: Where the allowed values come from.

        Returns:
            The term of each allowed value that belongs to a vocabulary.
        """
        return terms_by_name(self.schema, code, vocabularies)

    def problems(self) -> pandas.DataFrame:
        """Find what is wrong with the children.

        Returns:
            One line for each problem, with the columns ``row``, ``code``,
            ``column_name``, ``kind``, ``value``, ``suggestion``, ``rule`` and
            ``related``, ordered by row and then by the field's place in the schema.
            The lines of the rules come after the field lines of their row. ``rule``
            and ``related`` are set for a ``rule`` line only.
        """
        found = []
        for order, field in enumerate(self.schema.fields):
            if field.name in self.data.columns:
                found.append(self.field_problems(order, field))
            else:
                found.append(self.absent_problems(order, field))
        found += [rule.problems(self) for rule in self.rules]
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
                    "rule": None,
                    "related": None,
                    "order": order,
                }
            )
        )

    def rule_lines(
        self,
        rule: Rule,
        field: Field,
        values: pandas.Series,
        related: pandas.Series,
    ) -> pandas.DataFrame:
        """Build the problem lines for the cells of one field that break a rule.

        Args:
            rule: The rule that is broken.
            field: The field to fill or to change.
            values: The offending cells, indexed by row.
            related: What decided the rule applies, indexed by row.

        Returns:
            The problem lines, sorted after the field lines of their row.
        """
        lines = self.lines(
            len(self.schema.fields) + self.order(field), field, Kind.RULE, values
        )
        lines["rule"] = rule.identifier
        lines["related"] = related.reindex(values.index).to_numpy()
        return self.typed(lines)

    def order(self, field: Field) -> int:
        """Find a field's place in the schema.

        Args:
            field: The field.

        Returns:
            The field's position.
        """
        return [candidate.name for candidate in self.schema.fields].index(field.name)

    def holds(self, condition: Condition) -> pandas.Series:
        """Find the children a condition holds for.

        Args:
            condition: A field and the concepts that make a rule apply.

        Returns:
            For each child whether every value of the field is one of its allowed
            values and at least one is a term of the condition. An empty cell, a value
            that is not allowed and a field with no column never hold.
        """
        nowhere = pandas.Series(False, index=self.data.index)
        if condition.field not in self.data.columns:
            return nowhere
        field = self.schema.get_field(condition.field)
        column = self.data[condition.field].astype("string")
        values = self.each_value(field, column[~self.blank(column)])
        wanted = [self.terms[condition.field, name] for name in condition.concepts]
        allowed = values.isin(field.constraints.get("enum", []))
        held = (
            allowed.groupby(level=0).all() & values.isin(wanted).groupby(level=0).any()
        )
        return held.reindex(self.data.index, fill_value=False).astype(bool)

    def found(self, condition: Condition) -> pandas.Series:
        """Find the term of a condition each child holds.

        Args:
            condition: A field and the concepts that make a rule apply.

        Returns:
            For each child the condition holds for, the field's code, published column
            name and the first value found that is a term of the condition.
        """
        field = self.schema.get_field(condition.field)
        column = self.data[condition.field].astype("string")
        values = self.each_value(field, column[~self.blank(column)])
        wanted = [self.terms[condition.field, name] for name in condition.concepts]
        first = values[values.isin(wanted)]
        first = first[~first.index.duplicated()]
        label = f"{field.name} {field.custom['columnName']} "
        return label + first

    @staticmethod
    def blank(column: pandas.Series) -> pandas.Series:
        """Find the empty cells of a column.

        Args:
            column: A column of text.

        Returns:
            True where the cell is empty or holds spaces only.
        """
        return column.str.strip().fillna("").eq("")

    @staticmethod
    def is_required(field: Field) -> bool:
        """Say whether an empty cell in a field is a problem.

        Args:
            field: The field.

        Returns:
            True for a field mandatory in both domains, borehole and mine (``B``)
            and probe sensing (``S``).
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
        blank = self.blank(column)
        filled = column[~blank]
        constraints = field.constraints
        found = []
        if self.is_required(field):
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
        row of its cell. The scoring never splits text (``Inputs``): the schema gives
        no scored field a separator (docs/adr/0009).

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
        numbers = parse_numbers(filled)
        wrong = numbers.isna()
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
