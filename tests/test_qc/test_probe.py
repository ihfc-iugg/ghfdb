import json
from collections.abc import Mapping
from importlib import resources
from typing import Any

import pandas
import pytest
from frictionless import Schema

from ghfdb.fields import Vocabularies
from ghfdb.qc.probe import ProbeRules
from ghfdb.qc.scheme import Inputs, Terms

PARTS = ("probe-t",)
PROBE = "[Probing (offshore, ocean)]"


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


def rules_of(terms: Terms, data: pandas.DataFrame) -> ProbeRules:
    return ProbeRules(Inputs(data, terms))


class TestProbeTScore:
    @pytest.mark.parametrize(
        "example",
        [e for e in EXAMPLES if e["part"] == "probe-t"],
        ids=lambda example: example["id"],
    )
    def test_worked_example(self, terms: Terms, example: Mapping[str, Any]) -> None:
        rules = rules_of(terms, one_child(example["inputs"]))

        score = rules.t_score()

        assert score.value.iloc[0] == example["expected"]["T"]
        if "marked" in example["expected"]:
            assert score.marked.iloc[0] == example["expected"]["marked"]

    def test_the_own_score_applies_neither_waiver(self, terms: Terms) -> None:
        child = {
            "P12": PROBE,
            "C6": 5,
            "C37": 6,
            "C12": "[Tilt corrected]",
            "C17": "[Present and corrected]",
        }
        rules = rules_of(terms, one_child(child))

        child_score = rules.t_score()
        own_score = rules.own_t_score()

        assert (child_score.value.iloc[0], child_score.marked.iloc[0]) == (1.1, False)
        assert (own_score.value.iloc[0], own_score.marked.iloc[0]) == (0.7, True)

    def test_a_negative_tilt_takes_the_largest_penalty_without_the_mark(
        self, terms: Terms
    ) -> None:
        child = {"P12": PROBE, "P6": -3000, "C6": 5, "C37": 6, "C23": -1}

        score = rules_of(terms, one_child(child)).t_score()

        assert score.value.iloc[0] == 0.9
        assert not score.marked.iloc[0]

    def test_a_child_that_other_rules_score_is_not_determined(
        self, terms: Terms
    ) -> None:
        data = pandas.DataFrame(
            {"P12": ["[Drilling]", None, PROBE], "C6": ["5", "5", "5"]},
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
                "P12": [PROBE, PROBE, PROBE],
                "P6": ["-3000", "-3000", "-3000"],
                "C6": ["12", "0.5", "5"],
                "C23": ["0", "0", "20"],
                "C37": ["6", "6", "2"],
            },
            index=pandas.Index([12, 9, 10], name="row"),
            dtype=object,
        )

        score = rules_of(terms, data).t_score()

        assert score.value.index.tolist() == [12, 9, 10]
        assert score.value.tolist() == [1.2, 0.9, 0.8]

    def test_several_values_score_as_the_poorest(self, terms: Terms) -> None:
        child = {"P12": PROBE, "P6": -3000, "C6": [12, 0.5], "C23": 0, "C37": 6}

        score = rules_of(terms, one_child(child)).t_score()

        assert score.value.iloc[0] == 0.9
