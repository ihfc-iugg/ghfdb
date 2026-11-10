import json
from collections.abc import Mapping
from importlib import resources
from typing import Any

import pandas
import pytest

from ghfdb.qc.inputs import Inputs
from ghfdb.qc.uncertainty import UScore

PARTS = ("u-score",)


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


class TestUScore:
    @pytest.mark.parametrize("example", EXAMPLES, ids=lambda example: example["id"])
    def test_worked_example(self, example: Mapping[str, Any]) -> None:
        data = one_child(example["inputs"])

        scores = UScore(Inputs(data, {})).grades()

        assert scores.iloc[0] == example["expected"]["U"]

    def test_every_child_of_a_dataset_is_scored_under_its_own_index(self) -> None:
        data = pandas.DataFrame(
            {
                "C1": ["100", "100", None, "abc", "100", "0"],
                "C2": ["30", "4", "5", "5", "inf", "5"],
            },
            index=pandas.Index([14, 9, 10, 11, 12, 13], name="row"),
            dtype=object,
        )

        scores = UScore(Inputs(data, {})).grades()

        assert scores.index.tolist() == [14, 9, 10, 11, 12, 13]
        assert scores.tolist() == ["U4", "U1", "Ux", "Ux", "Ux", "Ux"]

    def test_several_values_score_as_the_poorest_pair(self) -> None:
        data = pandas.DataFrame(
            {"C1": [["100", "50"]], "C2": ["10"]},
            index=pandas.Index([9], name="row"),
            dtype=object,
        )

        scores = UScore(Inputs(data, {})).grades()

        assert scores.tolist() == ["U3"]
