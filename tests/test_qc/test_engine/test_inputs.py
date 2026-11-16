import pandas
import pytest
from conftest import column_children, field_concepts
from pandas.testing import assert_series_equal

from ghfdb.fields import Field
from ghfdb.fields.schema import FieldConcepts
from ghfdb.qc.engine.inputs import Inputs, parse_numbers
from ghfdb.vocabularies import concepts

METHOD = concepts.explo_method
DRILLING, MINING, PROBING = (
    str(METHOD.drilling),
    str(METHOD.mining),
    str(METHOD["probing-onshore"]),
)
NAMES: dict[str, FieldConcepts] = {
    Field.explo_method: field_concepts(
        {"[Drilling]": DRILLING, "[Mining]": MINING, "[Probing]": PROBING}
    )
}


class TestNumbers:
    def test_a_number_parses_as_the_check_parses_it(self) -> None:
        data = column_children(C1=["1.5", " 2 ", "abc", "inf", "-inf", "", None, "1e2"])

        numbers = Inputs(data, NAMES).numbers(Field.qc)

        expected = pandas.Series(
            [1.5, 2.0, None, None, None, None, None, 100.0],
            index=data.index,
            dtype="float64",
        )
        assert_series_equal(numbers, expected, check_names=False)

    def test_a_list_holds_several_values_one_row_each_under_the_childs_index(
        self,
    ) -> None:
        data = column_children(C1=["10", [1, "2"]])

        numbers = Inputs(data, NAMES).numbers(Field.qc)

        assert numbers.index.tolist() == [9, 10, 10]
        assert numbers.tolist() == [10.0, 1.0, 2.0]

    def test_text_is_never_split_into_several_values(self) -> None:
        data = column_children(C1=["1,2"])

        numbers = Inputs(data, NAMES).numbers(Field.qc)

        assert numbers.index.tolist() == [9]
        assert numbers.isna().all()

    def test_a_field_the_dataset_lacks_is_empty_for_every_child(self) -> None:
        data = column_children(P12=["[Drilling]", "[Mining]"])

        numbers = Inputs(data, NAMES).numbers(Field.qc)

        assert numbers.index.tolist() == [9, 10]
        assert numbers.isna().all()


class TestConcepts:
    def test_a_term_becomes_the_uri_of_its_concept(self) -> None:
        data = column_children(P12=["[Drilling]", "[Probing]", "[Mining]"])

        concepts = Inputs(data, NAMES).concepts(Field.explo_method)

        assert concepts.tolist() == [DRILLING, PROBING, MINING]

    def test_a_term_the_field_does_not_allow_is_empty(self) -> None:
        data = column_children(P12=["[Present and corrected]", "nonsense", "", None])

        concepts = Inputs(data, NAMES).concepts(Field.explo_method)

        assert concepts.isna().all()
        assert concepts.index.tolist() == data.index.tolist()

    def test_a_list_holds_several_values_one_row_each_under_the_childs_index(
        self,
    ) -> None:
        data = column_children(P12=["[Drilling]", ["[Mining]", "[Drilling]"]])

        concepts = Inputs(data, NAMES).concepts(Field.explo_method)

        assert concepts.index.tolist() == [9, 10, 10]
        assert concepts.tolist() == [DRILLING, MINING, DRILLING]

    def test_an_empty_list_is_one_empty_value(self) -> None:
        data = column_children(P12=[[], "[Drilling]"])

        concepts = Inputs(data, NAMES).concepts(Field.explo_method)

        assert concepts.index.tolist() == [9, 10]
        assert pandas.isna(concepts.iloc[0])

    def test_text_is_never_split_into_several_values(self) -> None:
        data = column_children(P12=["[Drilling], [Mining]"])

        concepts = Inputs(data, NAMES).concepts(Field.explo_method)

        assert concepts.index.tolist() == [9]
        assert concepts.isna().all()

    def test_a_field_the_dataset_lacks_is_empty_for_every_child(self) -> None:
        data = column_children(C1=["1", "2"])

        concepts = Inputs(data, NAMES).concepts(Field.explo_method)

        assert concepts.index.tolist() == [9, 10]
        assert concepts.isna().all()

    def test_a_field_without_declared_concepts_is_refused(self) -> None:
        data = column_children(P12=["[Drilling]"])

        with pytest.raises(KeyError, match="C42"):
            Inputs(data, NAMES).concepts(Field.tc_location)


class TestExpand:
    def test_a_collection_becomes_the_uris_of_its_members_and_a_concept_stays(
        self,
    ) -> None:
        resolved: dict[str, FieldConcepts] = {
            Field.explo_method: FieldConcepts(
                {METHOD.drilling: "[Drilling]", METHOD.mining: "[Mining]"},
                {METHOD.boreholes: (METHOD.drilling, METHOD.mining)},
            )
        }
        inputs = Inputs(column_children(P12=["[Drilling]"]), resolved)

        expanded = inputs.expand(
            Field.explo_method, [METHOD.boreholes, METHOD["probing-onshore"]]
        )

        assert expanded == (DRILLING, MINING, PROBING)
        assert all(type(uri) is str for uri in expanded)

    def test_a_field_without_declared_concepts_is_refused(self) -> None:
        with pytest.raises(KeyError, match="C42"):
            Inputs(column_children(P12=["[Drilling]"]), NAMES).expand(
                Field.tc_location, [METHOD.drilling]
            )


class TestPerChild:
    def test_the_first_value_of_each_child_is_the_one_kept(self) -> None:
        data = column_children(P12=[["[Mining]", "[Drilling]"], None, "[Drilling]"])
        inputs = Inputs(data, NAMES)

        first = inputs.first(inputs.concepts(Field.explo_method))

        assert first.index.tolist() == data.index.tolist()
        assert first.iloc[0] == MINING
        assert pandas.isna(first.iloc[1])
        assert first.iloc[2] == DRILLING

    def test_any_and_all_summarise_the_values_of_each_child(self) -> None:
        data = column_children(C1=[["1", "5"], ["5", "6"], None])
        inputs = Inputs(data, NAMES)
        above = inputs.numbers(Field.qc) > 3

        assert inputs.any_value(above).tolist() == [True, True, False]
        assert inputs.every_value(above).tolist() == [False, True, False]

    def test_a_child_is_filled_when_any_field_holds_a_value_that_is_not_blank(
        self,
    ) -> None:
        data = column_children(
            C1=["1", None, " ", [None, "2"], None],
            C2=[None, None, "", None, "abc"],
        )
        inputs = Inputs(data, NAMES)

        filled = inputs.any_filled([Field.qc, Field.qc_uncertainty])

        assert filled.tolist() == [True, False, False, True, True]

    def test_a_field_the_dataset_lacks_leaves_a_child_unfilled(self) -> None:
        inputs = Inputs(column_children(C1=["1", None]), NAMES)

        assert inputs.any_filled([Field.qc_uncertainty]).tolist() == [False, False]


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
