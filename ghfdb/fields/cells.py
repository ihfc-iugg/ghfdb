"""How the cells of a field are read: a number, and the term of a concept."""

import math

import pandas
from frictionless import Schema

from ghfdb.fields.schema import allowed_values
from ghfdb.fields.vocabularies import Vocabularies


def parse_numbers(text: pandas.Series) -> pandas.Series:
    """Read cells as numbers, the way the check and the scoring both read them.

    Args:
        text: The cells as text. Spaces around a number are ignored.

    Returns:
        The numbers as floats under the index of the cells, NaN where a cell is empty,
        is not a number or is infinite.
    """
    numbers = pandas.to_numeric(text.str.strip(), errors="coerce").astype("float64")
    return numbers.where(numbers.abs() != math.inf)


def concept_terms(
    schema: Schema, code: str, vocabularies: Vocabularies
) -> dict[str, str]:
    """Map the concept URI of each allowed value of a field to its term.

    Args:
        schema: The fields.
        code: The field's code.
        vocabularies: Where the allowed values come from.

    Returns:
        The term of each allowed value that belongs to a vocabulary, empty for a field
        that is not in the schema.
    """
    if not any(field.name == code for field in schema.fields):
        return {}
    return {
        value.uri: value.term
        for value in allowed_values(schema.get_field(code), vocabularies)
        if value.uri
    }
