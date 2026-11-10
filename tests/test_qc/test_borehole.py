import pandas
import pytest
from conftest import Uris, one_child

from ghfdb.fields import Field
from ghfdb.qc import borehole
from ghfdb.qc.borehole import BoreholeRules
from ghfdb.qc.inputs import Inputs
from ghfdb.qc.penalties import Band, Bands, Criterion
from ghfdb.qc.scores import Scores

DRILLING = "[Drilling]"
GRADIENT = {
    "P12": DRILLING,
    "C4": 0,
    "C5": 1000,
    "C37": 2,
    "C31": "[cBHT]",
    "C32": "[cBHT]",
}
CONDUCTIVITY = {
    "P12": DRILLING,
    "C4": 0,
    "C5": 1000,
    "C41": "[Core samples]",
    "C42": "[Actual heat-flow location]",
    "C44": "[Saturated measured]",
    "C45": "[Corrected in-situ (pT)]",
    "C47": 30,
}


def rules_of(uris: Uris, data: pandas.DataFrame) -> BoreholeRules:
    return Scores(Inputs(data, uris)).borehole


class TestBoreholeTScore:
    def test_an_empty_number_of_recordings_is_not_a_continuous_log_and_sets_no_mark(
        self, uris: Uris
    ) -> None:
        child = {**GRADIENT, "C31": "[LOGeq]", "C32": "[LOGeq]"}
        del child["C37"]

        score = rules_of(uris, one_child(child)).scores().t

        assert score.value.iloc[0] == 0.9
        assert not score.marked.iloc[0]

    def test_one_empty_method_leaves_the_other_to_decide_without_the_mark(
        self, uris: Uris
    ) -> None:
        child = {**GRADIENT, "C32": "[BHT]"}
        del child["C31"]

        score = rules_of(uris, one_child(child)).scores().t

        assert score.value.iloc[0] == 0.7
        assert not score.marked.iloc[0]

    def test_a_block_temperature_is_a_perturbed_single_point(self, uris: Uris) -> None:
        child = {**GRADIENT, "C31": "[BLK]", "C32": "[BLK]"}

        score = rules_of(uris, one_child(child)).scores().t

        assert score.value.iloc[0] == 0.7
        assert not score.marked.iloc[0]

    def test_a_surface_among_several_top_methods_leaves_the_bottom_to_decide(
        self, uris: Uris
    ) -> None:
        child = {**GRADIENT, "C31": ["[SUR]", "[CPD]"], "C32": "[cBHT]"}

        score = rules_of(uris, one_child(child)).scores().t

        assert score.value.iloc[0] == 0.7
        assert not score.marked.iloc[0]

    def test_a_surface_with_no_bottom_method_takes_the_largest_penalty_and_the_mark(
        self, uris: Uris
    ) -> None:
        child = {**GRADIENT, "C31": "[SUR]"}
        del child["C32"]

        score = rules_of(uris, one_child(child)).scores().t

        assert score.value.iloc[0] == 0.4
        assert score.marked.iloc[0]

    def test_a_log_among_several_recordings_is_a_continuous_log_only_if_all_pass(
        self, uris: Uris
    ) -> None:
        child = {**GRADIENT, "C37": [6, 2], "C31": "[LOGeq]", "C32": "[LOGeq]"}

        score = rules_of(uris, one_child(child)).scores().t

        assert score.value.iloc[0] == 0.9

    def test_a_child_that_other_rules_score_is_not_determined(self, uris: Uris) -> None:
        data = pandas.DataFrame(
            {
                "P12": ["[Probing (offshore, ocean)]", None, DRILLING],
                "C31": ["[cBHT]", "[cBHT]", "[cBHT]"],
                "C32": ["[cBHT]", "[cBHT]", "[cBHT]"],
            },
            index=pandas.Index([12, 9, 10], name="row"),
            dtype=object,
        )

        rules = rules_of(uris, data)

        for score in (rules.scores().t, rules.scores().own_t):
            assert score.value.isna().tolist() == [True, True, False]
            assert score.marked.isna().tolist() == [True, True, False]

    def test_a_child_with_every_scored_field_empty_is_not_determined(
        self, uris: Uris
    ) -> None:
        rules = rules_of(uris, one_child({"P12": DRILLING, "C31": " "}))

        for score in (rules.scores().t, rules.scores().own_t):
            assert score.value.isna().all()
            assert score.marked.isna().all()

    def test_one_filled_field_is_enough_to_score_the_child(self, uris: Uris) -> None:
        score = rules_of(uris, one_child({"P12": DRILLING, "C4": 0})).scores().t

        assert score.value.iloc[0] == 0.5
        assert score.marked.iloc[0]

    def test_every_child_of_a_dataset_is_scored_under_its_own_index(
        self, uris: Uris
    ) -> None:
        data = pandas.DataFrame(
            {
                "P12": [DRILLING, "[Mining]", "[Tunneling]"],
                "C37": ["5", "5", "2"],
                "C31": ["[LOGeq]", "[SUR]", "[CPD]"],
                "C32": ["[LOGeq]", "[BHT]", None],
            },
            index=pandas.Index([12, 9, 10], name="row"),
            dtype=object,
        )

        score = rules_of(uris, data).scores().t

        assert score.value.index.tolist() == [12, 9, 10]
        assert score.value.tolist() == [1.1, 0.5, 0.5]
        assert score.marked.tolist() == [False, False, False]


class TestBoreholeTCScore:
    def test_a_criterion_added_to_the_list_is_scored_in_both_scores(
        self, uris: Uris, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        extra = Criterion(
            "borehole-tc.extra",
            "Every child",
            Bands(Field.tc_number, (Band(-0.3),)),
            "Table 3",
        )
        monkeypatch.setattr(borehole, "TC_CRITERIA", (*borehole.TC_CRITERIA, extra))
        child = {**CONDUCTIVITY, "C11": "[Pressure and temperature considered]"}

        scores = rules_of(uris, one_child(child)).scores()

        assert scores.tc.value.iloc[0] == 0.7
        assert scores.own_tc.value.iloc[0] == 0.7

    def test_the_own_score_reads_the_pT_conditions_without_the_in_situ_correction(
        self, uris: Uris
    ) -> None:
        child = {**CONDUCTIVITY, "C11": "[Not considered]"}
        rules = rules_of(uris, one_child(child))

        child_score = rules.scores().tc
        own_score = rules.scores().own_tc

        assert (child_score.value.iloc[0], child_score.marked.iloc[0]) == (0.8, False)
        assert (own_score.value.iloc[0], own_score.marked.iloc[0]) == (1.0, False)

    def test_a_literature_location_leaves_the_number_out_and_sets_no_mark_for_it(
        self, uris: Uris
    ) -> None:
        child = {**CONDUCTIVITY, "C42": "[Literature or unspecified]"}
        del child["C47"]

        score = rules_of(uris, one_child(child)).scores().own_tc

        assert score.value.iloc[0] == 0.8
        assert not score.marked.iloc[0]

    def test_a_literature_location_among_several_leaves_the_number_to_the_rest(
        self, uris: Uris
    ) -> None:
        child = {
            **CONDUCTIVITY,
            "C42": ["[Actual heat-flow location]", "[Literature or unspecified]"],
        }
        del child["C47"]

        score = rules_of(uris, one_child(child)).scores().own_tc

        assert score.value.iloc[0] == 0.7
        assert score.marked.iloc[0]

    def test_the_gate_stops_the_scoring_of_every_other_criterion(
        self, uris: Uris
    ) -> None:
        child = {"P12": DRILLING, "C41": "[Other]", "C45": "[Unspecified]"}

        score = rules_of(uris, one_child(child)).scores().tc

        assert score.value.iloc[0] == 0.1
        assert score.marked.iloc[0]

    def test_a_child_with_every_scored_field_empty_is_not_determined(
        self, uris: Uris
    ) -> None:
        rules = rules_of(uris, one_child({"P12": DRILLING, "C41": " "}))

        for score in (rules.scores().tc, rules.scores().own_tc):
            assert score.value.isna().all()
            assert score.marked.isna().all()

    def test_one_filled_field_is_enough_to_score_the_child(self, uris: Uris) -> None:
        score = rules_of(uris, one_child({"P12": DRILLING, "C41": "[Other]"})).scores()

        assert score.tc.value.iloc[0] == 0.1
        assert score.tc.marked.iloc[0]

    def test_a_child_that_other_rules_score_is_not_determined(self, uris: Uris) -> None:
        data = pandas.DataFrame(
            {
                "P12": ["[Probing (offshore, ocean)]", None, DRILLING],
                "C41": ["[Other]", "[Other]", "[Other]"],
            },
            index=pandas.Index([12, 9, 10], name="row"),
            dtype=object,
        )

        rules = rules_of(uris, data)

        for score in (rules.scores().tc, rules.scores().own_tc):
            assert score.value.isna().tolist() == [True, True, False]
            assert score.marked.isna().tolist() == [True, True, False]

    def test_every_child_of_a_dataset_is_scored_under_its_own_index(
        self, uris: Uris
    ) -> None:
        data = pandas.DataFrame(
            {
                "P12": [DRILLING, DRILLING, "[Mining]"],
                "C4": ["0", None, "0"],
                "C41": ["[In-situ probe]", "[Core samples]", "[Cutting samples]"],
                "C42": ["[Actual heat-flow location]"] * 3,
                "C44": ["[Saturated measured]"] * 3,
                "C45": ["[Corrected in-situ (pT)]"] * 3,
                "C47": ["30", "30", "3"],
                "C11": [
                    "[Pressure and temperature considered]",
                    None,
                    "[Not considered]",
                ],
            },
            index=pandas.Index([12, 9, 10], name="row"),
            dtype=object,
        )

        score = rules_of(uris, data).scores().tc

        assert score.value.index.tolist() == [12, 9, 10]
        assert score.value.tolist() == [1.1, 0.1, 0.6]
        assert score.marked.tolist() == [False, True, False]
