from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas
import pytest
import responses
from example_site import publish
from frictionless import Schema
from pandas.testing import assert_series_equal

from ghfdb.fields import load_schema
from ghfdb.fields.cells import parse_numbers, terms_by_name
from ghfdb.vocabularies import (
    AllowedValue,
    MissingSchemeError,
    Vocabularies,
    caching_session,
)

COLOURS = "https://example.test/vocabularies/colours"
THREE_FIELDS = Path(__file__).parent / "schemas" / "three_fields.json"


@pytest.fixture
def vocabularies(web: responses.RequestsMock, tmp_path: Path) -> Vocabularies:
    publish(web, "colours")
    return Vocabularies(caching_session(tmp_path / "cache"))


@pytest.fixture
def three_fields(vocabularies: Vocabularies) -> Schema:
    return load_schema(THREE_FIELDS, vocabularies)


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


class Doubling(Vocabularies):
    """Vocabularies in which a second concept has the local name of the first."""

    def __init__(self, vocabularies: Vocabularies) -> None:
        self.vocabularies = vocabularies

    def allowed_values(self, vocabulary: Mapping[str, str | None]) -> Any:
        values = self.vocabularies.allowed_values(vocabulary)
        twin = AllowedValue(
            "[Twin]", "Twin", "https://example.test/elsewhere/red", None
        )
        return (*values, twin)


class TestTermsByName:
    def test_maps_the_local_name_of_each_concept_to_the_term_the_field_accepts(
        self, three_fields: Schema, vocabularies: Vocabularies
    ) -> None:
        terms = terms_by_name(three_fields, "X1", vocabularies)

        assert terms == {"red": "[red]", "orange": "[Orange]"}

    def test_gives_nothing_for_a_field_without_a_vocabulary(
        self, three_fields: Schema, vocabularies: Vocabularies
    ) -> None:
        assert terms_by_name(three_fields, "X3", vocabularies) == {}

    def test_gives_nothing_for_a_field_the_schema_lacks(
        self, three_fields: Schema, vocabularies: Vocabularies
    ) -> None:
        assert terms_by_name(three_fields, "Z99", vocabularies) == {}

    def test_refuses_two_allowed_values_with_one_local_name_naming_field_and_name(
        self, three_fields: Schema, vocabularies: Vocabularies
    ) -> None:
        with pytest.raises(MissingSchemeError, match="X1.*red"):
            terms_by_name(three_fields, "X1", Doubling(vocabularies))
