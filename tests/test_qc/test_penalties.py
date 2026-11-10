from typing import Any

import numpy
import pandas
import pytest
from conftest import column_children

from ghfdb.fields import Field
from ghfdb.qc.inputs import Inputs
from ghfdb.qc.penalties import (
    Band,
    Bands,
    Case,
    Cases,
    Classes,
    Criterion,
    Group,
    Penalty,
    Score,
)

RED, GREEN, BLUE = "c:red", "c:green", "c:blue"
SMALL, LARGE = "c:small", "c:large"
URIS: dict[str, dict[str, str]] = {
    Field.tc_location: {"[red]": RED, "[green]": GREEN, "[blue]": BLUE},
    Field.tc_method: {"[small]": SMALL, "[large]": LARGE},
}


def inputs_of(**columns: list[Any]) -> Inputs:
    return Inputs(column_children(**columns), URIS)


def penalties(penalty: Penalty) -> list[float]:
    return penalty.value.tolist()


def marks(penalty: Penalty) -> list[bool]:
    return penalty.marked.tolist()


class TestPenalty:
    def test_the_poorest_of_several_values_counts_under_the_childs_index(self) -> None:
        index = pandas.Index([12, 9, 10], name="row")
        values = pandas.Series([0.1, -0.1, 0.0, 0.0], index=[12, 9, 9, 10])
        marked = pandas.Series([False, False, True, False], index=values.index)

        poorest = Penalty(values, marked).poorest(index)

        assert poorest.value.index.tolist() == [12, 9, 10]
        assert penalties(poorest) == [0.1, -0.1, 0.0]

    def test_the_mark_comes_only_from_a_value_with_the_poorest_penalty(self) -> None:
        index = pandas.Index([9, 10])
        values = pandas.Series([-0.2, 0.0, -0.1, -0.1], index=[9, 9, 10, 10])
        marked = pandas.Series([False, True, True, False], index=values.index)

        poorest = Penalty(values, marked).poorest(index)

        assert marks(poorest) == [False, True]

    def test_choosing_takes_the_penalty_and_the_mark_of_the_first_condition_that_holds(
        self,
    ) -> None:
        index = pandas.Index([9, 10, 11])

        def uniform(value: float, mark: bool) -> Penalty:
            return Penalty(
                pandas.Series(value, index=index), pandas.Series(mark, index=index)
            )

        chosen = Penalty.choose(
            [numpy.array([True, False, False]), numpy.array([True, True, False])],
            [uniform(-0.1, True), uniform(-0.3, False)],
            uniform(-0.5, True),
        )

        assert penalties(chosen) == [-0.1, -0.3, -0.5]
        assert marks(chosen) == [True, False, True]

    def test_waiving_takes_away_the_penalty_and_the_mark(self) -> None:
        index = pandas.Index([9, 10])
        penalty = Penalty(
            pandas.Series([-0.2, -0.1], index=index),
            pandas.Series([True, True], index=index),
        )

        waived = penalty.waived(numpy.array([True, False]))

        assert penalties(waived) == [0.0, -0.1]
        assert marks(waived) == [False, True]


class TestScore:
    def test_adds_the_penalties_to_one_for_the_routed_children_only(self) -> None:
        index = pandas.Index([9, 10, 11])
        first = Penalty(
            pandas.Series([0.1, -0.2, 0.0], index=index),
            pandas.Series([False, False, False], index=index),
        )
        second = Penalty(
            pandas.Series([-0.1, 0.0, 0.0], index=index),
            pandas.Series([False, True, False], index=index),
        )

        score = Score.total([first, second], numpy.array([True, True, False]))

        assert score.value.tolist()[:2] == [1.0, 0.8]
        assert score.marked.tolist()[:2] == [False, True]
        assert score.value.isna().tolist() == [False, False, True]
        assert score.marked.isna().tolist() == [False, False, True]

    def test_rounds_away_the_error_of_adding_tenths(self) -> None:
        index = pandas.Index([9])
        tenth = Penalty(
            pandas.Series([0.1], index=index), pandas.Series([False], index=index)
        )

        score = Score.total([tenth, tenth, tenth], numpy.array([True]))

        assert score.value.iloc[0] == 1.3


class TestBands:
    PENETRATION = Bands(
        Field.probe_penetration,
        (Band(0.1, 10), Band(0.0, 3), Band(-0.1, 1), Band(-0.2)),
    )
    TILT = Bands(
        Field.probe_tilt,
        (Band(-0.2, 30), Band(-0.1, 10), Band(0.0, 0, inclusive=True)),
    )

    @pytest.mark.parametrize(
        ("cell", "expected"),
        [
            ("10.5", 0.1),
            ("10", 0.0),
            ("3.5", 0.0),
            ("3", -0.1),
            ("1.5", -0.1),
            ("1", -0.2),
            ("-4", -0.2),
        ],
    )
    def test_a_number_takes_the_penalty_of_the_highest_band_it_is_above(
        self, cell: str, expected: float
    ) -> None:
        penalty = self.PENETRATION.score(inputs_of(C6=[cell]))

        assert penalties(penalty) == [expected]
        assert marks(penalty) == [False]

    def test_an_edge_that_is_inclusive_belongs_to_its_band(self) -> None:
        inputs = inputs_of(C23=["0", "10", "10.1", "30", "30.1"])

        penalty = self.TILT.score(inputs)

        assert penalties(penalty) == [0.0, 0.0, -0.1, -0.1, -0.2]

    def test_an_empty_number_takes_the_empty_outcome_with_its_mark(self) -> None:
        inputs = inputs_of(C6=["", None, "abc"])

        penalty = self.PENETRATION.score(inputs)

        assert penalties(penalty) == [-0.2, -0.2, -0.2]
        assert marks(penalty) == [True, True, True]

    def test_a_number_that_fits_no_band_takes_the_unmatched_outcome(self) -> None:
        inputs = inputs_of(C23=["-1", "5"])

        penalty = self.TILT.score(inputs)

        assert penalties(penalty) == [-0.2, 0.0]
        assert marks(penalty) == [False, False]

    def test_the_empty_and_unmatched_penalty_is_the_largest_of_the_table(self) -> None:
        bands = Bands(Field.tc_number, (Band(0.0, 15), Band(-0.4, 5)))

        penalty = bands.score(inputs_of(C47=[None, "2", "20"]))

        assert penalties(penalty) == [-0.4, -0.4, 0.0]
        assert marks(penalty) == [True, False, False]

    def test_a_table_declares_only_whether_the_empty_and_unmatched_outcomes_mark(
        self,
    ) -> None:
        bands = Bands(
            Field.tc_number,
            (Band(0.0, 15), Band(-0.4, 5)),
            empty_marked=False,
            unmatched_marked=True,
        )

        penalty = bands.score(inputs_of(C47=[None, "2"]))

        assert penalties(penalty) == [-0.4, -0.4]
        assert marks(penalty) == [False, True]

    def test_several_values_keep_the_poorest(self) -> None:
        inputs = inputs_of(C6=[[12, 0.5], [12, ""], [12, 5]])

        penalty = self.PENETRATION.score(inputs)

        assert penalties(penalty) == [-0.2, -0.2, 0.0]
        assert marks(penalty) == [False, True, False]

    def test_a_value_is_left_out_where_another_field_holds_a_given_concept(
        self,
    ) -> None:
        bands = Bands(
            Field.tc_number,
            (Band(0.0, 3), Band(-0.2)),
            left_out_when={Field.tc_location: (RED,)},
        )
        inputs = inputs_of(
            C47=["1", None, "1", None, "1"],
            C42=["[green]", "[green]", "[red]", "[red]", [None, "[red]"]],
        )

        penalty = bands.score(inputs)

        assert penalties(penalty) == [-0.2, -0.2, 0.0, 0.0, -0.2]
        assert marks(penalty) == [False, True, False, False, False]

    def test_a_value_left_out_among_several_leaves_the_others_to_score(self) -> None:
        bands = Bands(
            Field.tc_number,
            (Band(0.0, 3), Band(-0.2)),
            left_out_when={Field.tc_location: (RED,)},
        )
        inputs = inputs_of(C47=[None], C42=[["[green]", "[red]"]])

        penalty = bands.score(inputs)

        assert penalties(penalty) == [-0.2]
        assert marks(penalty) == [True]

    def test_lists_what_it_reads_and_its_largest_penalty_for_the_documentation(
        self,
    ) -> None:
        bands = Bands(
            Field.tc_number,
            (Band(0.0, 3), Band(-0.2)),
            left_out_when={Field.tc_location: (RED,)},
        )

        assert bands.largest() == -0.2
        assert bands.reads() == (Field.tc_number, Field.tc_location)
        assert bands.concepts() == ((Field.tc_location, RED),)

    def test_a_band_selects_a_value_for_every_number_for_the_grades(self) -> None:
        bands = (Band(4, 25), Band(3, 15), Band(2, 5, inclusive=True), Band(1))

        chosen = Band.select(bands, pandas.Series([30.0, 25.0, 15.1, 5.0, 4.9]), 0)

        assert chosen.tolist() == [4, 3, 3, 2, 1]


class TestClasses:
    COLOURS = Classes(
        (Field.tc_location,),
        (Group(0.0, (RED, GREEN)), Group(-0.1, (BLUE,))),
        unmatched_marked=False,
    )

    def test_a_value_takes_the_penalty_of_its_group(self) -> None:
        inputs = inputs_of(C42=["[red]", "[green]", "[blue]"])

        penalty = self.COLOURS.score(inputs)

        assert penalties(penalty) == [0.0, 0.0, -0.1]
        assert marks(penalty) == [False, False, False]

    def test_an_empty_value_takes_the_empty_outcome_with_its_mark(self) -> None:
        inputs = inputs_of(C42=["", None, "nonsense"])

        penalty = self.COLOURS.score(inputs)

        assert penalties(penalty) == [-0.1, -0.1, -0.1]
        assert marks(penalty) == [True, True, True]

    def test_the_empty_and_unmatched_penalty_is_the_largest_of_the_table(self) -> None:
        uris: dict[str, dict[str, str]] = {
            Field.tc_location: {"[red]": RED, "[other]": "c:other"}
        }
        inputs = Inputs(column_children(C42=["[red]", "[other]", None]), uris)
        table = Classes(
            (Field.tc_location,),
            (Group(0.0, (RED,)), Group(-0.3, (BLUE,))),
            unmatched_marked=False,
        )

        penalty = table.score(inputs)

        assert penalties(penalty) == [0.0, -0.3, -0.3]
        assert marks(penalty) == [False, False, True]

    def test_a_concept_in_no_group_sets_the_mark_unless_the_table_says_not_to(
        self,
    ) -> None:
        uris: dict[str, dict[str, str]] = {
            Field.tc_location: {"[red]": RED, "[other]": "c:other"}
        }
        inputs = Inputs(column_children(C42=["[other]"]), uris)
        groups = (Group(0.0, (RED,)), Group(-0.3, (BLUE,)))

        marked = Classes((Field.tc_location,), groups).score(inputs)
        unmarked = Classes((Field.tc_location,), groups, unmatched_marked=False).score(
            inputs
        )

        assert marks(marked) == [True]
        assert marks(unmarked) == [False]

    def test_several_values_keep_the_poorest_and_its_mark(self) -> None:
        inputs = inputs_of(C42=[["[red]", "[blue]"], ["[blue]", None], ["[red]"]])

        penalty = self.COLOURS.score(inputs)

        assert penalties(penalty) == [-0.1, -0.1, 0.0]
        assert marks(penalty) == [False, True, False]

    def test_the_values_of_several_fields_are_scored_together(self) -> None:
        uris: dict[str, dict[str, str]] = {
            Field.T_method_top: {"[red]": RED, "[blue]": BLUE},
            Field.T_method_bottom: {"[red]": RED, "[blue]": BLUE},
        }
        data = column_children(C31=["[red]", "[blue]"], C32=["[blue]", "[red]"])
        table = Classes(
            (Field.T_method_top, Field.T_method_bottom),
            (Group(0.0, (RED,)), Group(-0.1, (BLUE,))),
        )

        penalty = table.score(Inputs(data, uris))

        assert penalties(penalty) == [-0.1, -0.1]

    def test_an_empty_value_is_left_out_when_the_table_says_so_and_another_is_filled(
        self,
    ) -> None:
        uris: dict[str, dict[str, str]] = {
            Field.T_method_top: {"[red]": RED, "[blue]": BLUE},
            Field.T_method_bottom: {"[red]": RED, "[blue]": BLUE},
        }
        data = column_children(C31=[None, None, "[blue]"], C32=["[red]", None, "[red]"])
        table = Classes(
            (Field.T_method_top, Field.T_method_bottom),
            (Group(0.0, (RED,)), Group(-0.5, (BLUE,))),
            skip_empty=True,
        )

        penalty = table.score(Inputs(data, uris))

        assert penalties(penalty) == [0.0, -0.5, -0.5]
        assert marks(penalty) == [False, True, False]

    def test_tells_which_values_fit_a_group(self) -> None:
        concepts = pandas.Series([RED, BLUE, "c:other", None], dtype="string")

        assert self.COLOURS.fits(concepts).tolist() == [True, True, False, False]

    def test_lists_what_it_reads_and_its_largest_penalty_for_the_documentation(
        self,
    ) -> None:
        assert self.COLOURS.largest() == -0.1
        assert self.COLOURS.reads() == (Field.tc_location,)
        assert self.COLOURS.concepts() == (
            (Field.tc_location, RED),
            (Field.tc_location, GREEN),
            (Field.tc_location, BLUE),
        )


class TestCases:
    TABLE = Cases(
        (
            Case(0.1, {Field.tc_location: (RED,), Field.tc_method: (SMALL,)}),
            Case(0.0, {Field.tc_location: (RED, GREEN)}),
            Case(-0.1, {Field.tc_method: (LARGE,)}),
        )
    )

    def test_the_poorest_case_whose_conditions_all_hold_counts(self) -> None:
        inputs = inputs_of(
            C42=["[red]", "[red]", "[green]", "[red]"],
            C43=["[small]", "[large]", "[small]", None],
        )

        penalty = self.TABLE.score(inputs)

        assert penalties(penalty)[:3] == [0.0, -0.1, 0.0]

    def test_a_row_holds_whatever_a_field_it_does_not_name_contains(self) -> None:
        inputs = inputs_of(C42=["[green]", "[red]"], C43=[None, None])

        penalty = self.TABLE.score(inputs)

        assert penalties(penalty) == [0.0, 0.0]
        assert marks(penalty) == [False, False]

    def test_no_row_holding_with_an_empty_field_a_row_names_takes_the_empty_outcome(
        self,
    ) -> None:
        inputs = inputs_of(C42=[None, "[blue]"], C43=["[small]", None])

        penalty = self.TABLE.score(inputs)

        assert penalties(penalty) == [-0.1, -0.1]
        assert marks(penalty) == [True, True]

    def test_the_empty_and_unmatched_penalty_is_the_largest_of_the_table(self) -> None:
        inputs = inputs_of(C42=["[blue]", None], C43=["[small]", "[small]"])

        penalty = self.TABLE.score(inputs)

        assert penalties(penalty) == [-0.1, -0.1]
        assert marks(penalty) == [False, True]

    def test_no_case_holding_takes_the_unmatched_outcome(self) -> None:
        inputs = inputs_of(C42=["[blue]"], C43=["[small]"])

        penalty = self.TABLE.score(inputs)

        assert penalties(penalty) == [-0.1]
        assert marks(penalty) == [False]

    def test_several_values_are_scored_in_every_combination_and_the_poorest_counts(
        self,
    ) -> None:
        inputs = inputs_of(
            C42=[["[red]", "[blue]"], "[red]"], C43=["[small]", "[small]"]
        )

        penalty = self.TABLE.score(inputs)

        assert penalties(penalty) == [-0.1, 0.0]
        assert marks(penalty) == [False, False]

    def test_lists_what_it_reads_and_its_largest_penalty_for_the_documentation(
        self,
    ) -> None:
        assert self.TABLE.largest() == -0.1
        assert self.TABLE.reads() == (Field.tc_location, Field.tc_method)
        assert self.TABLE.concepts() == (
            (Field.tc_location, RED),
            (Field.tc_method, SMALL),
            (Field.tc_location, GREEN),
            (Field.tc_method, LARGE),
        )

    def test_a_row_that_needs_every_value_of_a_field_holds_only_when_all_of_them_do(
        self,
    ) -> None:
        table = Cases(
            (
                Case(
                    0.0, {Field.tc_location: (RED,)}, every={Field.tc_method: (SMALL,)}
                ),
                Case(-0.2, {Field.tc_location: (BLUE,)}),
            )
        )
        inputs = inputs_of(
            C42=["[red]", "[red]", "[red]"],
            C43=[["[small]", "[small]"], ["[small]", "[large]"], "[small]"],
        )

        penalty = table.score(inputs)

        assert penalties(penalty) == [0.0, -0.2, 0.0]
        assert marks(penalty) == [False, False, False]

    def test_lists_the_fields_and_concepts_of_a_row_that_needs_every_value(
        self,
    ) -> None:
        table = Cases(
            (Case(0.0, {Field.tc_location: (RED,)}, every={Field.tc_method: (SMALL,)}),)
        )

        assert table.reads() == (Field.tc_location, Field.tc_method)
        assert table.concepts() == (
            (Field.tc_location, RED),
            (Field.tc_method, SMALL),
        )


class TestCriterion:
    def test_scores_with_its_table_and_says_what_it_reads(self) -> None:
        criterion = Criterion(
            "x.location",
            "A location",
            TestClasses.COLOURS,
            "Table 1, Location",
        )

        penalty = criterion.score(inputs_of(C42=["[green]"]))

        assert penalties(penalty) == [0.0]
        assert criterion.concepts() == TestClasses.COLOURS.concepts()
