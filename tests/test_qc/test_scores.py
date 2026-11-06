import json
from collections.abc import Mapping
from importlib import import_module, resources
from typing import Any

import pandas
import pytest
from frictionless import Schema

from ghfdb.fields import Vocabularies
from ghfdb.qc.scheme import Inputs, Terms
from ghfdb.qc.scores import Scores

NOT_DETERMINED = "not determined"
# The modules that run worked examples, each exposing the examples it runs as EXAMPLES.
RUNNING = ("test_uncertainty", "test_scores", "test_probe")
# The parts no code scores yet. The group that builds a part removes it from here.
PENDING = {"borehole-t", "borehole-tc", "m-score", "child"}


def load_examples(part: str) -> list[Mapping[str, Any]]:
    text = (resources.files("ghfdb.qc") / "worked_examples.json").read_text("utf-8")
    examples: list[Mapping[str, Any]] = json.loads(text)["examples"]
    return [example for example in examples if example["part"] == part]


ROUTING = load_examples("routing")
FLAGS = load_examples("perturbation-flags")
# Every example this module runs, which the coverage test reads.
EXAMPLES = [*ROUTING, *FLAGS]


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


class TestRouting:
    @pytest.mark.parametrize("example", ROUTING, ids=lambda example: example["id"])
    def test_worked_example(self, terms: Terms, example: Mapping[str, Any]) -> None:
        data = one_child(example["inputs"])
        wanted = example["expected"].get("rules")

        rules = Scores(Inputs(data, terms), terms).routing()

        if wanted in (None, NOT_DETERMINED):
            assert pandas.isna(rules.iloc[0])
        else:
            assert rules.iloc[0] == wanted

    def test_every_child_of_a_dataset_is_routed_under_its_own_index(
        self, terms: Terms
    ) -> None:
        data = pandas.DataFrame(
            {"P12": ["[Drilling]", None, "[Probing (clustered)]", "[Other]"]},
            index=pandas.Index([12, 9, 10, 11], name="row"),
            dtype=object,
        )

        rules = Scores(Inputs(data, terms), terms).routing()

        assert rules.index.tolist() == [12, 9, 10, 11]
        assert rules.iloc[0] == "borehole and mine"
        assert rules.iloc[2] == "probe sensing"
        assert rules.iloc[[1, 3]].isna().all()


class TestWorkedExampleCoverage:
    def test_every_example_outside_inheritance_is_run_by_exactly_one_test(self) -> None:
        text = (resources.files("ghfdb.qc") / "worked_examples.json").read_text("utf-8")
        examples = json.loads(text)["examples"]
        expected = sorted(
            example["id"]
            for example in examples
            if example["part"] != "inheritance" and example["part"] not in PENDING
        )

        run = sorted(
            example["id"]
            for name in RUNNING
            for example in import_module(f"{__package__}.{name}").EXAMPLES
        )

        assert run == expected


class TestPerturbationFlags:
    @pytest.mark.parametrize("example", FLAGS, ids=lambda example: example["id"])
    def test_worked_example(self, terms: Terms, example: Mapping[str, Any]) -> None:
        data = one_child(example["inputs"])

        flags = Scores(Inputs(data, terms), terms).flags()

        assert flags.iloc[0] == example["expected"]["flags"]

    def test_every_child_of_a_dataset_gets_its_own_flags_under_its_own_index(
        self, terms: Terms
    ) -> None:
        data = pandas.DataFrame(
            {
                "C13": ["[Present and corrected]", None, "[Unspecified]"],
                "C19": ["[Not recognized]", "[Present and not significant]", "x"],
            },
            index=pandas.Index([12, 9, 10], name="row"),
            dtype=object,
        )

        flags = Scores(Inputs(data, terms), terms).flags()

        assert flags.index.tolist() == [12, 9, 10]
        assert flags.tolist() == ["S-----x", "------X", "-------"]
