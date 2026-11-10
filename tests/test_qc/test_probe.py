import json
from collections.abc import Mapping
from importlib import resources
from typing import Any

import pandas
import pytest
from frictionless import Schema

from ghfdb.fields import Vocabularies
from ghfdb.qc.criteria import term_uris
from ghfdb.qc.inputs import Inputs
from ghfdb.qc.probe import ProbeRules
from ghfdb.qc.scores import Scores

Uris = dict[str, dict[str, str]]

PARTS = ("probe-t", "probe-tc")
PROBE = "[Probing (offshore, ocean)]"
BEST_CONDUCTIVITY = {
    "P12": PROBE,
    "C41": "[In-situ probe]",
    "C42": "[Actual heat-flow location]",
    "C43": "[Probe - pulse technique]",
    "C44": "[Saturated measured in-situ]",
    "C45": "[Actual in-situ (pT) conditions]",
    "C47": 4,
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


def rules_of(uris: Uris, data: pandas.DataFrame) -> ProbeRules:
    return Scores(Inputs(data, uris)).probe


class TestProbeTScore:
    @pytest.mark.parametrize(
        "example",
        [e for e in EXAMPLES if e["part"] == "probe-t"],
        ids=lambda example: example["id"],
    )
    def test_worked_example(self, uris: Uris, example: Mapping[str, Any]) -> None:
        rules = rules_of(uris, one_child(example["inputs"]))

        score = rules.scores().t

        assert score.value.iloc[0] == example["expected"]["T"]
        if "marked" in example["expected"]:
            assert score.marked.iloc[0] == example["expected"]["marked"]

    def test_the_own_score_applies_neither_waiver(self, uris: Uris) -> None:
        child = {
            "P12": PROBE,
            "C6": 5,
            "C37": 6,
            "C12": "[Tilt corrected]",
            "C17": "[Present and corrected]",
        }
        rules = rules_of(uris, one_child(child))

        child_score = rules.scores().t
        own_score = rules.scores().own_t

        assert (child_score.value.iloc[0], child_score.marked.iloc[0]) == (1.1, False)
        assert (own_score.value.iloc[0], own_score.marked.iloc[0]) == (0.7, True)

    def test_a_negative_tilt_takes_the_largest_penalty_without_the_mark(
        self, uris: Uris
    ) -> None:
        child = {"P12": PROBE, "P6": -3000, "C6": 5, "C37": 6, "C23": -1}

        score = rules_of(uris, one_child(child)).scores().t

        assert score.value.iloc[0] == 0.9
        assert not score.marked.iloc[0]

    def test_a_child_that_other_rules_score_is_not_determined(self, uris: Uris) -> None:
        data = pandas.DataFrame(
            {"P12": ["[Drilling]", None, PROBE], "C6": ["5", "5", "5"]},
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
                "P12": [PROBE, PROBE, PROBE],
                "P6": ["-3000", "-3000", "-3000"],
                "C6": ["12", "0.5", "5"],
                "C23": ["0", "0", "20"],
                "C37": ["6", "6", "2"],
            },
            index=pandas.Index([12, 9, 10], name="row"),
            dtype=object,
        )

        score = rules_of(uris, data).scores().t

        assert score.value.index.tolist() == [12, 9, 10]
        assert score.value.tolist() == [1.2, 0.9, 0.8]

    def test_several_values_score_as_the_poorest(self, uris: Uris) -> None:
        child = {"P12": PROBE, "P6": -3000, "C6": [12, 0.5], "C23": 0, "C37": 6}

        score = rules_of(uris, one_child(child)).scores().t

        assert score.value.iloc[0] == 0.9


class TestProbeTCScore:
    @pytest.mark.parametrize(
        "example",
        [e for e in EXAMPLES if e["part"] == "probe-tc"],
        ids=lambda example: example["id"],
    )
    def test_worked_example(self, uris: Uris, example: Mapping[str, Any]) -> None:
        rules = rules_of(uris, one_child(example["inputs"]))

        score = rules.scores().tc

        assert score.value.iloc[0] == example["expected"]["TC"]
        if "marked" in example["expected"]:
            assert score.marked.iloc[0] == example["expected"]["marked"]
        own = rules.scores().own_tc
        assert own.value.equals(score.value)
        assert own.marked.equals(score.marked)

    def test_a_method_that_fits_no_saturation_case_takes_no_mark(
        self, uris: Uris
    ) -> None:
        child = {
            **BEST_CONDUCTIVITY,
            "C43": "[Probe - continuous heating technique]",
        }

        score = rules_of(uris, one_child(child)).scores().tc

        assert score.value.iloc[0] == 0.6
        assert not score.marked.iloc[0]

    def test_a_method_estimated_from_other_properties_is_scored_without_the_mark(
        self, uris: Uris
    ) -> None:
        child = {
            **BEST_CONDUCTIVITY,
            "C43": "[Estimation - from water content-porosity]",
            "C45": "[Corrected in-situ (pT)]",
        }

        score = rules_of(uris, one_child(child)).scores().tc

        assert score.value.iloc[0] == 0.8
        assert not score.marked.iloc[0]

    def test_a_literature_location_among_several_leaves_the_number_to_the_rest(
        self, uris: Uris
    ) -> None:
        child = {
            **BEST_CONDUCTIVITY,
            "C42": ["[Actual heat-flow location]", "[Literature or unspecified]"],
        }
        del child["C47"]

        score = rules_of(uris, one_child(child)).scores().tc

        assert score.value.iloc[0] == 0.8
        assert score.marked.iloc[0]

    def test_a_child_that_other_rules_score_is_not_determined(self, uris: Uris) -> None:
        data = pandas.DataFrame(
            {"P12": ["[Mining]", PROBE], "C47": ["4", "4"]},
            index=pandas.Index([12, 9], name="row"),
            dtype=object,
        )

        score = rules_of(uris, data).scores().tc

        assert score.value.isna().tolist() == [True, False]
        assert score.marked.isna().tolist() == [True, False]

    def test_every_child_of_a_dataset_is_scored_under_its_own_index(
        self, uris: Uris
    ) -> None:
        data = pandas.DataFrame(
            {
                "P12": [PROBE, PROBE],
                "C41": ["[In-situ probe]", None],
                "C42": ["[Actual heat-flow location]", "[Other location]"],
                "C43": ["[Probe - pulse technique]", "[Probe - pulse technique]"],
                "C44": ["[Saturated measured in-situ]", "[Recovered]"],
                "C45": ["[Actual in-situ (pT) conditions]", "[Corrected in-situ (pT)]"],
                "C47": ["4", "1"],
            },
            index=pandas.Index([12, 9], name="row"),
            dtype=object,
        )

        score = rules_of(uris, data).scores().tc

        assert score.value.index.tolist() == [12, 9]
        assert score.value.tolist() == [1.2, 0.5]
        assert score.marked.tolist() == [False, True]
