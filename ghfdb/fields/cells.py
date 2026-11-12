"""How the cells of a field are read: a number."""

import math

import pandas


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
