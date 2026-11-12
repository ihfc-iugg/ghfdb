import pandas
from pandas.testing import assert_series_equal

from ghfdb.fields.cells import parse_numbers


class TestParseNumbers:
    def test_reads_a_number_as_a_float_ignoring_surrounding_spaces(self) -> None:
        text = pandas.Series(["1.5", " 2 ", "1e2", "-3"], dtype="string")

        numbers = parse_numbers(text)

        assert numbers.tolist() == [1.5, 2.0, 100.0, -3.0]
        assert numbers.dtype == "float64"

    def test_leaves_what_is_not_a_finite_number_empty(self) -> None:
        text = pandas.Series(["abc", "inf", "-inf", "", None, "nan"], dtype="string")

        numbers = parse_numbers(text)

        assert numbers.isna().all()
        assert numbers.index.tolist() == text.index.tolist()

    def test_keeps_the_index_of_its_cells(self) -> None:
        text = pandas.Series(["1", "2"], index=[12, 9], dtype="string")

        numbers = parse_numbers(text)

        assert_series_equal(
            numbers, pandas.Series([1.0, 2.0], index=[12, 9]), check_names=False
        )
