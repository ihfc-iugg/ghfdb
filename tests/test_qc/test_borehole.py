import json
from collections.abc import Mapping
from importlib import resources
from typing import Any

import pandas
import pytest
from frictionless import Schema

from ghfdb.fields import Vocabularies
from ghfdb.qc.borehole import BoreholeRules
from ghfdb.qc.scheme import Inputs, Terms

PARTS = ("borehole-t",)
DRILLING = "[Drilling]"
GRADIENT = {
    "P12": DRILLING,
    "C4": 0,
    "C5": 1000,
    "C37": 2,
    "C31": "[cBHT]",
    "C32": "[cBHT]",
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
def terms(schema: Schema, published_vocabularies: Vocabularies) -> Terms:
    return Terms(schema, published_vocabularies)


def rules_of(terms: Terms, data: pandas.DataFrame) -> BoreholeRules:
    return BoreholeRules(Inputs(data, terms))


class TestBoreholeTScore:
    @pytest.mark.parametrize(
        "example",
        [e for e in EXAMPLES if e["part"] == "borehole-t"],
        ids=lambda example: example["id"],
    )
    def test_worked_example(self, terms: Terms, example: Mapping[str, Any]) -> None:
        rules = rules_of(terms, one_child(example["inputs"]))

        score = rules.t_score()

        assert score.value.iloc[0] == example["expected"]["T"]
        if "marked" in example["expected"]:
            assert score.marked.iloc[0] == example["expected"]["marked"]
        own = rules.own_t_score()
        assert own.value.equals(score.value)
        assert own.marked.equals(score.marked)

    def test_an_empty_number_of_recordings_is_not_a_continuous_log_and_sets_no_mark(
        self, terms: Terms
    ) -> None:
        child = {**GRADIENT, "C31": "[LOGeq]", "C32": "[LOGeq]"}
        del child["C37"]

        score = rules_of(terms, one_child(child)).t_score()

        assert score.value.iloc[0] == 0.9
        assert not score.marked.iloc[0]

    def test_one_empty_method_leaves_the_other_to_decide_without_the_mark(
        self, terms: Terms
    ) -> None:
        child = {**GRADIENT, "C32": "[BHT]"}
        del child["C31"]

        score = rules_of(terms, one_child(child)).t_score()

        assert score.value.iloc[0] == 0.7
        assert not score.marked.iloc[0]

    def test_a_surface_among_several_top_methods_leaves_the_bottom_to_decide(
        self, terms: Terms
    ) -> None:
        child = {**GRADIENT, "C31": ["[SUR]", "[CPD]"], "C32": "[cBHT]"}

        score = rules_of(terms, one_child(child)).t_score()

        assert score.value.iloc[0] == 0.7
        assert not score.marked.iloc[0]

    def test_a_surface_with_no_bottom_method_takes_the_largest_penalty_and_the_mark(
        self, terms: Terms
    ) -> None:
        child = {**GRADIENT, "C31": "[SUR]"}
        del child["C32"]

        score = rules_of(terms, one_child(child)).t_score()

        assert score.value.iloc[0] == 0.4
        assert score.marked.iloc[0]

    def test_a_log_among_several_recordings_is_a_continuous_log_only_if_all_pass(
        self, terms: Terms
    ) -> None:
        child = {**GRADIENT, "C37": [6, 2], "C31": "[LOGeq]", "C32": "[LOGeq]"}

        score = rules_of(terms, one_child(child)).t_score()

        assert score.value.iloc[0] == 0.9

    def test_a_child_that_other_rules_score_is_not_determined(
        self, terms: Terms
    ) -> None:
        data = pandas.DataFrame(
            {
                "P12": ["[Probing (offshore, ocean)]", None, DRILLING],
                "C31": ["[cBHT]", "[cBHT]", "[cBHT]"],
                "C32": ["[cBHT]", "[cBHT]", "[cBHT]"],
            },
            index=pandas.Index([12, 9, 10], name="row"),
            dtype=object,
        )

        rules = rules_of(terms, data)

        for score in (rules.t_score(), rules.own_t_score()):
            assert score.value.isna().tolist() == [True, True, False]
            assert score.marked.isna().tolist() == [True, True, False]

    def test_every_child_of_a_dataset_is_scored_under_its_own_index(
        self, terms: Terms
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

        score = rules_of(terms, data).t_score()

        assert score.value.index.tolist() == [12, 9, 10]
        assert score.value.tolist() == [1.1, 0.5, 0.5]
        assert score.marked.tolist() == [False, False, False]
