from collections.abc import Callable, Mapping
from typing import Any

import pandas
import pytest
from frictionless import Field, Schema

Children = Callable[..., pandas.DataFrame]


def first_field(schema: Schema, wanted: Callable[[Field], bool]) -> Field:
    return next(field for field in schema.fields if wanted(field))


def mandatory_everywhere(field: Field) -> bool:
    obligation, domain = field.custom["obligation"], field.custom["domain"]
    return obligation == "M" and set(domain) == {"B", "S"}


@pytest.fixture
def number_field(schema: Schema) -> Field:
    return first_field(
        schema,
        lambda f: f.type == "number" and {"minimum", "maximum"} <= set(f.constraints),
    )


@pytest.fixture
def integer_field(schema: Schema) -> Field:
    return first_field(schema, lambda f: f.type == "integer")


@pytest.fixture
def pattern_field(schema: Schema) -> Field:
    return first_field(schema, lambda f: "pattern" in f.constraints)


@pytest.fixture
def vocabulary_field(schema: Schema) -> Field:
    return first_field(
        schema, lambda f: "enum" in f.constraints and mandatory_everywhere(f)
    )


@pytest.fixture
def length_field(schema: Schema) -> Field:
    return first_field(schema, lambda f: "maxLength" in f.constraints)


@pytest.fixture
def mandatory_field(schema: Schema) -> Field:
    return first_field(schema, lambda f: mandatory_everywhere(f) and f.type == "string")


@pytest.fixture
def recommended_field(schema: Schema) -> Field:
    return first_field(schema, lambda f: f.custom["obligation"] == "R")


@pytest.fixture
def one_domain_mandatory_field(schema: Schema) -> Field:
    return first_field(
        schema,
        lambda f: f.custom["obligation"] == "M"
        and set(f.custom["domain"]) != {"B", "S"},
    )


@pytest.fixture
def children(schema: Schema, valid_child: dict[str, Any]) -> Children:
    """Build a table of children from Excel row 9: a valid child changed per row.

    Each argument is the changes to one child, by field code. A value is written as
    text and ``None`` leaves the cell empty.
    """

    def build(*changes: Mapping[str, Any]) -> pandas.DataFrame:
        rows = [
            {
                code: None if value is None else str(value)
                for code, value in (valid_child | dict(change)).items()
            }
            for change in changes
        ]
        frame = pandas.DataFrame(rows, columns=[f.name for f in schema.fields])
        frame.index = pandas.Index(range(9, 9 + len(rows)), name="row")
        return frame.astype("string")

    return build
