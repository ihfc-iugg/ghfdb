import json
from collections.abc import Mapping
from importlib import import_module, resources
from typing import Any

import pandas
import pytest
from frictionless import Schema

from ghfdb.dataset import Dataset
from ghfdb.fields import Vocabularies
from ghfdb.qc.criteria import term_uris
from ghfdb.qc.inputs import Inputs
from ghfdb.qc.penalties import Score
from ghfdb.qc.scores import Scores

Uris = dict[str, dict[str, str]]

NOT_DETERMINED = "not determined"
# The modules that run worked examples, each exposing the examples it runs as EXAMPLES.
RUNNING = ("test_uncertainty", "test_scores", "test_probe", "test_borehole")
# The parts no code scores yet. The group that builds a part removes it from here.
PENDING: set[str] = set()


def load_examples(part: str) -> list[Mapping[str, Any]]:
    text = (resources.files("ghfdb.qc") / "worked_examples.json").read_text("utf-8")
    examples: list[Mapping[str, Any]] = json.loads(text)["examples"]
    return [example for example in examples if example["part"] == part]


ROUTING = load_examples("routing")
FLAGS = load_examples("perturbation-flags")
M_SCORE = load_examples("m-score")
CHILD = load_examples("child")
# Every example this module runs, which the coverage test reads.
EXAMPLES = [*ROUTING, *FLAGS, *M_SCORE, *CHILD]


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


class TestRouting:
    @pytest.mark.parametrize("example", ROUTING, ids=lambda example: example["id"])
    def test_worked_example(self, uris: Uris, example: Mapping[str, Any]) -> None:
        data = one_child(example["inputs"])
        wanted = example["expected"].get("rules")

        rules = Scores(Inputs(data, uris)).routing

        if wanted in (None, NOT_DETERMINED):
            assert pandas.isna(rules.iloc[0])
        else:
            assert rules.iloc[0] == wanted

    def test_every_child_of_a_dataset_is_routed_under_its_own_index(
        self, uris: Uris
    ) -> None:
        data = pandas.DataFrame(
            {"P12": ["[Drilling]", None, "[Probing (clustered)]", "[Other]"]},
            index=pandas.Index([12, 9, 10, 11], name="row"),
            dtype=object,
        )

        rules = Scores(Inputs(data, uris)).routing

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
    def test_worked_example(self, uris: Uris, example: Mapping[str, Any]) -> None:
        data = one_child(example["inputs"])

        flags = Scores(Inputs(data, uris)).flags()

        assert flags.iloc[0] == example["expected"]["flags"]

    def test_every_child_of_a_dataset_gets_its_own_flags_under_its_own_index(
        self, uris: Uris
    ) -> None:
        data = pandas.DataFrame(
            {
                "C13": ["[Present and corrected]", None, "[Unspecified]"],
                "C19": ["[Not recognized]", "[Present and not significant]", "x"],
            },
            index=pandas.Index([12, 9, 10], name="row"),
            dtype=object,
        )

        flags = Scores(Inputs(data, uris)).flags()

        assert flags.index.tolist() == [12, 9, 10]
        assert flags.tolist() == ["S-----x", "------X", "-------"]


def sub_score(value: Any, marked: bool) -> Score:
    """Build the score of one child from an example's value and mark."""
    number = pandas.NA if value == NOT_DETERMINED else value
    return Score(
        pandas.Series([number], index=[9], dtype="Float64"),
        pandas.Series([pandas.NA if number is pandas.NA else marked], dtype="boolean"),
    )


class TestMScore:
    @pytest.mark.parametrize("example", M_SCORE, ids=lambda example: example["id"])
    def test_worked_example(self, uris: Uris, example: Mapping[str, Any]) -> None:
        inputs = example["inputs"]
        t = sub_score(inputs["T"], inputs.get("T_marked", False))
        tc = sub_score(inputs["TC"], inputs.get("TC_marked", False))

        grade = Scores(Inputs(one_child({}), uris)).grades(t, tc)

        assert grade.iloc[0] == example["expected"]["M"]

    def test_every_child_is_graded_under_its_own_index(self, uris: Uris) -> None:
        index = pandas.Index([12, 9, 10, 11], name="row")
        t = Score(
            pandas.Series([1.0, 0.5, pandas.NA, 0.3], index=index, dtype="Float64"),
            pandas.Series(
                [False, True, pandas.NA, False], index=index, dtype="boolean"
            ),
        )
        tc = Score(
            pandas.Series([0.8, 0.5, 0.9, 0.3], index=index, dtype="Float64"),
            pandas.Series([False, False, False, False], index=index, dtype="boolean"),
        )

        grade = Scores(Inputs(pandas.DataFrame(index=index), uris)).grades(t, tc)

        assert grade.index.tolist() == [12, 9, 10, 11]
        assert grade.tolist() == ["M1", "M3x", "Mx", "M4"]


class TestChildScores:
    @pytest.mark.parametrize("example", CHILD, ids=lambda example: example["id"])
    def test_worked_example(
        self, published_vocabularies: Vocabularies, example: Mapping[str, Any]
    ) -> None:
        data = one_child(example["inputs"])
        expected = example["expected"]

        row = Dataset(data).scores(vocabularies=published_vocabularies).iloc[0]

        for key in ("U", "T", "TC", "M", "flags", "code", "marked"):
            if key in expected:
                wanted = expected[key]
                if wanted is None:
                    assert pandas.isna(row[key]), key
                else:
                    assert row[key] == wanted, key
        for key, column in (("T", "own_T"), ("TC", "own_TC")):
            if "measurement" in expected:
                assert row[column] == expected["measurement"][key], column
