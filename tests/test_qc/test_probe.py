import pandas
import pytest
from conftest import ScoredConcepts, one_child

from ghfdb.fields import Field
from ghfdb.qc import probe
from ghfdb.qc.criteria import CRITERIA
from ghfdb.qc.engine.inputs import Inputs
from ghfdb.qc.engine.tables import Band, Bands, Criterion
from ghfdb.qc.probe import ProbeSensing
from ghfdb.qc.scores import Scores

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


def rules_of(scored_concepts: ScoredConcepts, data: pandas.DataFrame) -> ProbeSensing:
    return Scores(Inputs(data, scored_concepts)).probe


class TestWaterDepth:
    def score(self, scored_concepts: ScoredConcepts, elevation: float) -> float:
        inputs = Inputs(one_child({"P6": elevation}), scored_concepts)

        return float(CRITERIA["probe-t.water-depth"].score(inputs).value.iloc[0])

    def test_the_criterion_scores_the_depth_below_sea_level_whatever_scores_it(
        self, scored_concepts: ScoredConcepts
    ) -> None:
        assert self.score(scored_concepts, -3000) == 0.0
        assert self.score(scored_concepts, -2000) == -0.1
        assert self.score(scored_concepts, -1000) == -0.2

    def test_an_elevation_at_or_above_sea_level_has_no_depth_and_is_empty(
        self, scored_concepts: ScoredConcepts
    ) -> None:
        inputs = Inputs(one_child({"P6": 0}), scored_concepts)

        penalty = CRITERIA["probe-t.water-depth"].score(inputs)

        assert penalty.value.iloc[0] == -0.2
        assert penalty.marked.iloc[0]


class TestProbeTScore:
    def test_a_criterion_added_to_the_list_is_scored(
        self, scored_concepts: ScoredConcepts, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        extra = Criterion(
            "probe-t.extra",
            "Every child",
            Bands(Field.T_number, (Band(-0.3),)),
            "Table 2",
        )
        monkeypatch.setattr(probe, "T_CRITERIA", (*probe.T_CRITERIA, extra))
        child = {"P12": PROBE, "P6": -3000, "C6": 5, "C37": 6, "C23": 0}

        score = rules_of(scored_concepts, one_child(child)).scores().t

        assert score.value.iloc[0] == 0.8

    def test_the_own_score_applies_neither_waiver(
        self, scored_concepts: ScoredConcepts
    ) -> None:
        child = {
            "P12": PROBE,
            "C6": 5,
            "C37": 6,
            "C12": "[Tilt corrected]",
            "C17": "[Present and corrected]",
        }
        rules = rules_of(scored_concepts, one_child(child))

        child_score = rules.scores().t
        own_score = rules.scores().own_t

        assert (child_score.value.iloc[0], child_score.marked.iloc[0]) == (1.1, False)
        assert (own_score.value.iloc[0], own_score.marked.iloc[0]) == (0.7, True)

    def test_a_negative_tilt_takes_the_largest_penalty_without_the_mark(
        self, scored_concepts: ScoredConcepts
    ) -> None:
        child = {"P12": PROBE, "P6": -3000, "C6": 5, "C37": 6, "C23": -1}

        score = rules_of(scored_concepts, one_child(child)).scores().t

        assert score.value.iloc[0] == 0.9
        assert not score.marked.iloc[0]

    def test_a_child_that_other_rules_score_is_not_determined(
        self, scored_concepts: ScoredConcepts
    ) -> None:
        data = pandas.DataFrame(
            {"P12": ["[Drilling]", None, PROBE], "C6": ["5", "5", "5"]},
            index=pandas.Index([12, 9, 10], name="row"),
            dtype=object,
        )

        rules = rules_of(scored_concepts, data)

        for score in (rules.scores().t, rules.scores().own_t):
            assert score.value.isna().tolist() == [True, True, False]
            assert score.marked.isna().tolist() == [True, True, False]

    def test_a_child_with_every_scored_field_empty_is_not_determined(
        self, scored_concepts: ScoredConcepts
    ) -> None:
        rules = rules_of(scored_concepts, one_child({"P12": PROBE, "C6": " "}))

        for score in (rules.scores().t, rules.scores().own_t):
            assert score.value.isna().all()
            assert score.marked.isna().all()

    def test_one_filled_field_is_enough_to_score_the_child(
        self, scored_concepts: ScoredConcepts
    ) -> None:
        score = (
            rules_of(scored_concepts, one_child({"P12": PROBE, "C37": 6})).scores().t
        )

        assert score.value.iloc[0] == 0.5
        assert score.marked.iloc[0]

    def test_every_child_of_a_dataset_is_scored_under_its_own_index(
        self, scored_concepts: ScoredConcepts
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

        score = rules_of(scored_concepts, data).scores().t

        assert score.value.index.tolist() == [12, 9, 10]
        assert score.value.tolist() == [1.2, 0.9, 0.8]

    def test_several_values_score_as_the_poorest(
        self, scored_concepts: ScoredConcepts
    ) -> None:
        child = {"P12": PROBE, "P6": -3000, "C6": [12, 0.5], "C23": 0, "C37": 6}

        score = rules_of(scored_concepts, one_child(child)).scores().t

        assert score.value.iloc[0] == 0.9


class TestProbeTCScore:
    def test_a_method_that_fits_no_saturation_case_takes_no_mark(
        self, scored_concepts: ScoredConcepts
    ) -> None:
        child = {
            **BEST_CONDUCTIVITY,
            "C43": "[Probe - continuous heating technique]",
        }

        score = rules_of(scored_concepts, one_child(child)).scores().tc

        assert score.value.iloc[0] == 0.6
        assert not score.marked.iloc[0]

    def test_a_method_estimated_from_other_properties_is_scored_without_the_mark(
        self, scored_concepts: ScoredConcepts
    ) -> None:
        child = {
            **BEST_CONDUCTIVITY,
            "C43": "[Estimation - from water content-porosity]",
            "C45": "[Corrected in-situ (pT)]",
        }

        score = rules_of(scored_concepts, one_child(child)).scores().tc

        assert score.value.iloc[0] == 0.8
        assert not score.marked.iloc[0]

    def test_a_literature_location_among_several_leaves_the_number_to_the_rest(
        self, scored_concepts: ScoredConcepts
    ) -> None:
        child = {
            **BEST_CONDUCTIVITY,
            "C42": ["[Actual heat-flow location]", "[Literature or unspecified]"],
        }
        del child["C47"]

        score = rules_of(scored_concepts, one_child(child)).scores().tc

        assert score.value.iloc[0] == 0.8
        assert score.marked.iloc[0]

    def test_a_child_that_other_rules_score_is_not_determined(
        self, scored_concepts: ScoredConcepts
    ) -> None:
        data = pandas.DataFrame(
            {"P12": ["[Mining]", PROBE], "C47": ["4", "4"]},
            index=pandas.Index([12, 9], name="row"),
            dtype=object,
        )

        score = rules_of(scored_concepts, data).scores().tc

        assert score.value.isna().tolist() == [True, False]
        assert score.marked.isna().tolist() == [True, False]

    def test_a_child_with_every_scored_field_empty_is_not_determined(
        self, scored_concepts: ScoredConcepts
    ) -> None:
        rules = rules_of(scored_concepts, one_child({"P12": PROBE, "C41": " "}))

        for score in (rules.scores().tc, rules.scores().own_tc):
            assert score.value.isna().all()
            assert score.marked.isna().all()

    def test_one_filled_field_is_enough_to_score_the_child(
        self, scored_concepts: ScoredConcepts
    ) -> None:
        score = (
            rules_of(scored_concepts, one_child({"P12": PROBE, "C6": 12})).scores().tc
        )

        assert score.value.iloc[0] == 0.2
        assert score.marked.iloc[0]

    def test_every_child_of_a_dataset_is_scored_under_its_own_index(
        self, scored_concepts: ScoredConcepts
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

        score = rules_of(scored_concepts, data).scores().tc

        assert score.value.index.tolist() == [12, 9]
        assert score.value.tolist() == [1.2, 0.5]
        assert score.marked.tolist() == [False, True]
