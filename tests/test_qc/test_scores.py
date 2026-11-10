from collections.abc import Callable, Mapping
from typing import Any

import pandas
import pytest
from conftest import Example, Uris, examples_of, one_child

from ghfdb.dataset import Dataset
from ghfdb.fields import Vocabularies
from ghfdb.qc.inputs import Inputs
from ghfdb.qc.penalties import Score
from ghfdb.qc.scores import Scores
from ghfdb.qc.uncertainty import UScore

NOT_DETERMINED = "not determined"


def sub_score(value: Any, marked: bool) -> Score:
    """Build the score of one child from an example's value and mark."""
    number = pandas.NA if value == NOT_DETERMINED else value
    return Score(
        pandas.Series([number], index=[9], dtype="Float64"),
        pandas.Series([pandas.NA if number is pandas.NA else marked], dtype="boolean"),
    )


def assert_score(score: Score, expected: Mapping[str, Any], key: str) -> None:
    """Assert a one-child score is the expected value and, when given, the mark."""
    assert score.value.iloc[0] == expected[key]
    if "marked" in expected:
        assert score.marked.iloc[0] == expected["marked"]


class ExampleRunner:
    """Score one worked example as the scoring does and assert what it expects.

    Args:
        uris: The URI of every concept the scoring reads.
        vocabularies: The published vocabularies the whole dataset scoring reads.
    """

    def __init__(self, uris: Uris, vocabularies: Vocabularies) -> None:
        self.uris = uris
        self.vocabularies = vocabularies

    def scores(self, example: Example) -> Scores:
        """Build the scoring of the one child an example describes."""
        return Scores(Inputs(one_child(example["inputs"]), self.uris))

    def u_score(self, example: Example) -> None:
        grades = UScore(Inputs(one_child(example["inputs"]), {})).grades()

        assert grades.iloc[0] == example["expected"]["U"]

    def routing(self, example: Example) -> None:
        wanted = example["expected"].get("rules")

        rules = self.scores(example).routing

        if wanted in (None, NOT_DETERMINED):
            assert pandas.isna(rules.iloc[0])
        else:
            assert rules.iloc[0] == wanted

    def flags(self, example: Example) -> None:
        flags = self.scores(example).flags()

        assert flags.iloc[0] == example["expected"]["flags"]

    def m_score(self, example: Example) -> None:
        inputs = example["inputs"]
        t = sub_score(inputs["T"], inputs.get("T_marked", False))
        tc = sub_score(inputs["TC"], inputs.get("TC_marked", False))

        grade = Scores(Inputs(one_child({}), self.uris)).grades(t, tc)

        assert grade.iloc[0] == example["expected"]["M"]

    def probe_t(self, example: Example) -> None:
        assert_score(self.scores(example).probe.scores().t, example["expected"], "T")

    def probe_tc(self, example: Example) -> None:
        scores = self.scores(example).probe.scores()

        assert_score(scores.tc, example["expected"], "TC")
        assert scores.own_tc.value.equals(scores.tc.value)
        assert scores.own_tc.marked.equals(scores.tc.marked)

    def borehole_t(self, example: Example) -> None:
        scores = self.scores(example).borehole.scores()

        assert_score(scores.t, example["expected"], "T")
        assert scores.own_t.value.equals(scores.t.value)
        assert scores.own_t.marked.equals(scores.t.marked)

    def borehole_tc(self, example: Example) -> None:
        scores = self.scores(example).borehole.scores()

        score = scores.own_tc if example["scoring"] == "measurement" else scores.tc

        assert_score(score, example["expected"], "TC")

    def child(self, example: Example) -> None:
        data = one_child(example["inputs"])
        expected = example["expected"]

        row = Dataset(data).scores(vocabularies=self.vocabularies).iloc[0]

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


# The runner of each part of the worked examples. A part with no runner here has its
# examples left out of RUN, which TestWorkedExamples reports.
RUNNERS: dict[str, Callable[[ExampleRunner, Example], None]] = {
    "u-score": ExampleRunner.u_score,
    "routing": ExampleRunner.routing,
    "perturbation-flags": ExampleRunner.flags,
    "m-score": ExampleRunner.m_score,
    "probe-t": ExampleRunner.probe_t,
    "probe-tc": ExampleRunner.probe_tc,
    "borehole-t": ExampleRunner.borehole_t,
    "borehole-tc": ExampleRunner.borehole_tc,
    "child": ExampleRunner.child,
}
RUN = [example for example in examples_of() if example["part"] in RUNNERS]


class TestWorkedExamples:
    def test_every_example_outside_inheritance_has_a_runner(self) -> None:
        wanted = sorted(
            example["id"]
            for example in examples_of()
            if example["part"] != "inheritance"
        )

        assert sorted(example["id"] for example in RUN) == wanted

    @pytest.mark.parametrize("example", RUN, ids=lambda example: example["id"])
    def test_every_example_scores_as_expected(
        self, uris: Uris, published_vocabularies: Vocabularies, example: Example
    ) -> None:
        runner = ExampleRunner(uris, published_vocabularies)

        RUNNERS[example["part"]](runner, example)


class TestScoreTable:
    def test_each_column_holds_what_its_name_says(
        self, published_vocabularies: Vocabularies
    ) -> None:
        child = {
            "P12": "[Probing (offshore, ocean)]",
            "C6": 5,
            "C37": 6,
            "C12": "[Tilt corrected]",
            "C17": "[Present and corrected]",
        }

        scores = Dataset(one_child(child)).scores(vocabularies=published_vocabularies)

        assert scores.iloc[0].to_dict() == {
            "rules": "probe sensing",
            "U": "Ux",
            "T": 1.1,
            "TC": 0.2,
            "marked": True,
            "M": "M4x",
            "flags": "----V--",
            "code": "Ux.M4x.----V--",
            "own_T": 0.7,
            "own_TC": 0.2,
            "own_T_marked": True,
            "own_TC_marked": True,
        }


class TestRouting:
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


class TestPerturbationFlags:
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


class TestMScore:
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
