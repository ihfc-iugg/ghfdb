from typing import Any

import pandas
import pytest
from pandas.testing import assert_series_equal

from ghfdb.fields import Field
from ghfdb.qc.concepts import DRILLING, MINING, PROBING_ONSHORE
from ghfdb.qc.inputs import Inputs

URIS: dict[str, dict[str, str]] = {
    Field.explo_method: {
        "[Drilling]": DRILLING,
        "[Mining]": MINING,
        "[Probing]": PROBING_ONSHORE,
    }
}


def children(**columns: list[Any]) -> pandas.DataFrame:
    """Build children from Excel row 9: one list of cells for each field code."""
    rows = len(next(iter(columns.values())))
    index = pandas.Index(range(9, 9 + rows), name="row")
    return pandas.DataFrame(columns, index=index, dtype=object)


class TestNumbers:
    def test_a_number_parses_as_the_check_parses_it(self) -> None:
        data = children(C1=["1.5", " 2 ", "abc", "inf", "-inf", "", None, "1e2"])

        numbers = Inputs(data, URIS).numbers(Field.qc)

        expected = pandas.Series(
            [1.5, 2.0, None, None, None, None, None, 100.0],
            index=data.index,
            dtype="float64",
        )
        assert_series_equal(numbers, expected, check_names=False)

    def test_a_list_holds_several_values_one_row_each_under_the_childs_index(
        self,
    ) -> None:
        data = children(C1=["10", [1, "2"]])

        numbers = Inputs(data, URIS).numbers(Field.qc)

        assert numbers.index.tolist() == [9, 10, 10]
        assert numbers.tolist() == [10.0, 1.0, 2.0]

    def test_text_is_never_split_into_several_values(self) -> None:
        data = children(C1=["1,2"])

        numbers = Inputs(data, URIS).numbers(Field.qc)

        assert numbers.index.tolist() == [9]
        assert numbers.isna().all()

    def test_a_field_the_dataset_lacks_is_empty_for_every_child(self) -> None:
        data = children(P12=["[Drilling]", "[Mining]"])

        numbers = Inputs(data, URIS).numbers(Field.qc)

        assert numbers.index.tolist() == [9, 10]
        assert numbers.isna().all()


class TestConcepts:
    def test_a_term_becomes_the_uri_of_its_concept(self) -> None:
        data = children(P12=["[Drilling]", "[Probing]", "[Mining]"])

        concepts = Inputs(data, URIS).concepts(Field.explo_method)

        assert concepts.tolist() == [DRILLING, PROBING_ONSHORE, MINING]

    def test_a_term_the_field_does_not_allow_is_empty(self) -> None:
        data = children(P12=["[Present and corrected]", "nonsense", "", None])

        concepts = Inputs(data, URIS).concepts(Field.explo_method)

        assert concepts.isna().all()
        assert concepts.index.tolist() == data.index.tolist()

    def test_a_list_holds_several_values_one_row_each_under_the_childs_index(
        self,
    ) -> None:
        data = children(P12=["[Drilling]", ["[Mining]", "[Drilling]"]])

        concepts = Inputs(data, URIS).concepts(Field.explo_method)

        assert concepts.index.tolist() == [9, 10, 10]
        assert concepts.tolist() == [DRILLING, MINING, DRILLING]

    def test_an_empty_list_is_one_empty_value(self) -> None:
        data = children(P12=[[], "[Drilling]"])

        concepts = Inputs(data, URIS).concepts(Field.explo_method)

        assert concepts.index.tolist() == [9, 10]
        assert pandas.isna(concepts.iloc[0])

    def test_text_is_never_split_into_several_values(self) -> None:
        data = children(P12=["[Drilling], [Mining]"])

        concepts = Inputs(data, URIS).concepts(Field.explo_method)

        assert concepts.index.tolist() == [9]
        assert concepts.isna().all()

    def test_a_field_the_dataset_lacks_is_empty_for_every_child(self) -> None:
        data = children(C1=["1", "2"])

        concepts = Inputs(data, URIS).concepts(Field.explo_method)

        assert concepts.index.tolist() == [9, 10]
        assert concepts.isna().all()

    def test_a_field_without_declared_concepts_is_refused(self) -> None:
        data = children(P12=["[Drilling]"])

        with pytest.raises(KeyError, match="C42"):
            Inputs(data, URIS).concepts(Field.tc_location)


class TestPerChild:
    def test_the_first_value_of_each_child_is_the_one_kept(self) -> None:
        data = children(P12=[["[Mining]", "[Drilling]"], None, "[Drilling]"])
        inputs = Inputs(data, URIS)

        first = inputs.first(inputs.concepts(Field.explo_method))

        assert first.index.tolist() == data.index.tolist()
        assert first.iloc[0] == MINING
        assert pandas.isna(first.iloc[1])
        assert first.iloc[2] == DRILLING

    def test_any_and_all_summarise_the_values_of_each_child(self) -> None:
        data = children(C1=[["1", "5"], ["5", "6"], None])
        inputs = Inputs(data, URIS)
        above = inputs.numbers(Field.qc) > 3

        assert inputs.any_value(above).tolist() == [True, True, False]
        assert inputs.every_value(above).tolist() == [False, True, False]

    def test_a_child_is_filled_when_any_field_holds_a_value_that_is_not_blank(
        self,
    ) -> None:
        data = children(
            C1=["1", None, " ", [None, "2"], None],
            C2=[None, None, "", None, "abc"],
        )
        inputs = Inputs(data, URIS)

        filled = inputs.any_filled([Field.qc, Field.qc_uncertainty])

        assert filled.tolist() == [True, False, False, True, True]

    def test_a_field_the_dataset_lacks_leaves_a_child_unfilled(self) -> None:
        inputs = Inputs(children(C1=["1", None]), URIS)

        assert inputs.any_filled([Field.qc_uncertainty]).tolist() == [False, False]
