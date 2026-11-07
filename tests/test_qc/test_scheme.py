import re
from typing import Any

import pandas
import pytest
from frictionless import Schema
from pandas.testing import assert_series_equal

from ghfdb.fields import MissingSchemeError, Vocabularies, allowed_values
from ghfdb.qc.rules import DRILLING, EXPLORATION_METHOD, MINING, PROBING_ONSHORE
from ghfdb.qc.scheme import (
    CONCEPTS,
    FLAG_FIELDS,
    PRESENT_CORRECTED,
    Inputs,
    Terms,
)

SCORED_TERM_FIELDS = (
    "C11",
    "C12",
    "C31",
    "C32",
    "C41",
    "C42",
    "C43",
    "C44",
    "C45",
)


@pytest.fixture(scope="module")
def terms(schema: Schema, published_vocabularies: Vocabularies) -> Terms:
    return Terms(schema, published_vocabularies)


def children(**columns: list[Any]) -> pandas.DataFrame:
    """Build children from Excel row 9: one list of cells for each field code."""
    rows = len(next(iter(columns.values())))
    index = pandas.Index(range(9, 9 + rows), name="row")
    return pandas.DataFrame(columns, index=index, dtype=object)


class TestTerms:
    def test_every_concept_resolves_to_the_term_its_field_accepts_when_published(
        self, schema: Schema, published_vocabularies: Vocabularies, terms: Terms
    ) -> None:
        for code, uri in CONCEPTS:
            field = schema.get_field(code)
            accepted = {
                v.uri: v.term for v in allowed_values(field, published_vocabularies)
            }

            assert terms.term(code, uri) == accepted[uri], (code, uri)

    def test_the_scheme_names_the_fields_whose_terms_it_scores(self) -> None:
        codes = {code for code, _ in CONCEPTS}

        assert codes == {EXPLORATION_METHOD, *FLAG_FIELDS, *SCORED_TERM_FIELDS}

    def test_a_concept_the_field_does_not_allow_fails_naming_it(
        self, schema: Schema, published_vocabularies: Vocabularies
    ) -> None:
        withdrawn = (*CONCEPTS, (EXPLORATION_METHOD, PRESENT_CORRECTED))

        with pytest.raises(MissingSchemeError, match=re.escape(PRESENT_CORRECTED)):
            Terms(schema, published_vocabularies, withdrawn)

    def test_a_concept_of_a_field_outside_the_schema_fails_naming_it(
        self, schema: Schema, published_vocabularies: Vocabularies
    ) -> None:
        unknown = (*CONCEPTS, ("Z99", DRILLING))

        with pytest.raises(MissingSchemeError, match="Z99"):
            Terms(schema, published_vocabularies, unknown)


class TestInputs:
    def test_a_number_parses_as_the_check_parses_it(self, terms: Terms) -> None:
        data = children(C1=["1.5", " 2 ", "abc", "inf", "-inf", "", None, "1e2"])

        numbers = Inputs(data, terms).numbers["C1"]

        expected = pandas.Series(
            [1.5, 2.0, None, None, None, None, None, 100.0],
            index=data.index,
            dtype="float64",
        )
        assert_series_equal(numbers, expected, check_names=False)

    def test_a_term_becomes_the_uri_of_its_concept(self, terms: Terms) -> None:
        data = children(
            P12=["[Drilling]", "[Probing (onshore, lake, river, etc.)]", "[Mining]"]
        )

        concepts = Inputs(data, terms).concepts[EXPLORATION_METHOD]

        assert concepts.tolist() == [DRILLING, PROBING_ONSHORE, MINING]

    def test_a_term_the_field_does_not_allow_is_empty(self, terms: Terms) -> None:
        data = children(P12=["[Present and corrected]", "nonsense", "", None])

        concepts = Inputs(data, terms).concepts[EXPLORATION_METHOD]

        assert concepts.isna().all()
        assert concepts.index.tolist() == data.index.tolist()

    def test_a_list_holds_several_values_one_row_each_under_the_childs_index(
        self, terms: Terms
    ) -> None:
        data = children(
            P12=["[Drilling]", ["[Mining]", "[Drilling]"]],
            C1=["10", [1, "2"]],
        )

        inputs = Inputs(data, terms)

        assert inputs.concepts[EXPLORATION_METHOD].index.tolist() == [9, 10, 10]
        assert inputs.concepts[EXPLORATION_METHOD].tolist() == [
            DRILLING,
            MINING,
            DRILLING,
        ]
        assert inputs.numbers["C1"].index.tolist() == [9, 10, 10]
        assert inputs.numbers["C1"].tolist() == [10.0, 1.0, 2.0]

    def test_an_empty_list_is_one_empty_value(self, terms: Terms) -> None:
        data = children(P12=[[], "[Drilling]"])

        concepts = Inputs(data, terms).concepts[EXPLORATION_METHOD]

        assert concepts.index.tolist() == [9, 10]
        assert pandas.isna(concepts.iloc[0])

    def test_text_is_never_split_into_several_values(self, terms: Terms) -> None:
        data = children(P12=["[Drilling], [Mining]"], C1=["1,2"])

        inputs = Inputs(data, terms)

        assert inputs.concepts[EXPLORATION_METHOD].index.tolist() == [9]
        assert inputs.concepts[EXPLORATION_METHOD].isna().all()
        assert inputs.numbers["C1"].isna().all()

    def test_a_field_the_dataset_lacks_is_empty_for_every_child(
        self, terms: Terms
    ) -> None:
        data = children(P12=["[Drilling]", "[Mining]"])

        inputs = Inputs(data, terms)

        assert inputs.numbers["C1"].index.tolist() == [9, 10]
        assert inputs.numbers["C1"].isna().all()
        assert inputs.concepts["C13"].index.tolist() == [9, 10]
        assert inputs.concepts["C13"].isna().all()

    def test_the_first_value_of_each_child_is_the_one_kept(self, terms: Terms) -> None:
        data = children(
            P12=[["[Mining]", "[Drilling]"], None, "[Drilling]"],
        )
        inputs = Inputs(data, terms)

        first = inputs.first(inputs.concepts[EXPLORATION_METHOD])

        assert first.index.tolist() == data.index.tolist()
        assert first.iloc[0] == MINING
        assert pandas.isna(first.iloc[1])
        assert first.iloc[2] == DRILLING
