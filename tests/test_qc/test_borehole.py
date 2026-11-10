import json
from collections.abc import Mapping
from importlib import resources
from typing import Any

import pandas
import pytest
from frictionless import Schema

from ghfdb.fields import Vocabularies
from ghfdb.qc.borehole import BoreholeRules
from ghfdb.qc.criteria import term_uris
from ghfdb.qc.inputs import Inputs
from ghfdb.qc.scores import Scores

Uris = dict[str, dict[str, str]]

PARTS = ("borehole-t", "borehole-tc")
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


def load_examples() -> list[Mapping[str, Any]]:
    text = (resources.files("ghfdb.qc") / "worked_examples.json").read_text("utf-8")
    examples: list[Mapping[str, Any]] = json.loads(text)["examples"]
    return [example for example in examples if example["part"] in PARTS]


EXAMPLES = load_examples()


def one_child(inputs: Mapping[str, Any]) -> pandas.DataFrame:
    """Build a dataset of one child from an example: numbers as text, lists kept."""
    cells = {
        code: [value if isinstance(value, list) else str(value)]
        for code, value in inputs.items()
    }
    return pandas.DataFrame(cells, index=pandas.Index([9], name="row"), dtype=object)


@pytest.fixture(scope="module")
def uris(schema: Schema, published_vocabularies: Vocabularies) -> Uris:
    return term_uris(schema, Scores.concepts(), published_vocabularies)


def rules_of(uris: Uris, data: pandas.DataFrame) -> BoreholeRules:
    return Scores(Inputs(data, uris)).borehole


class TestBoreholeTScore:
    @pytest.mark.parametrize(
        "example",
        [e for e in EXAMPLES if e["part"] == "borehole-t"],
        ids=lambda example: example["id"],
    )
    def test_worked_example(self, uris: Uris, example: Mapping[str, Any]) -> None:
        rules = rules_of(uris, one_child(example["inputs"]))

        score = rules.scores().t

        assert score.value.iloc[0] == example["expected"]["T"]
        if "marked" in example["expected"]:
            assert score.marked.iloc[0] == example["expected"]["marked"]
        own = rules.scores().own_t
        assert own.value.equals(score.value)
        assert own.marked.equals(score.marked)

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
    @pytest.mark.parametrize(
        "example",
        [e for e in EXAMPLES if e["part"] == "borehole-tc"],
        ids=lambda example: example["id"],
    )
    def test_worked_example(self, uris: Uris, example: Mapping[str, Any]) -> None:
        rules = rules_of(uris, one_child(example["inputs"]))

        if example["scoring"] == "measurement":
            score = rules.scores().own_tc
        else:
            score = rules.scores().tc

        assert score.value.iloc[0] == example["expected"]["TC"]
        if "marked" in example["expected"]:
            assert score.marked.iloc[0] == example["expected"]["marked"]

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

    def test_a_child_that_other_rules_score_is_not_determined(self, uris: Uris) -> None:
        data = pandas.DataFrame(
            {"P12": ["[Probing (offshore, ocean)]", None, DRILLING]},
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
