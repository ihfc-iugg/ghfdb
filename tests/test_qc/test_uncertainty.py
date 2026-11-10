import pandas

from ghfdb.qc.inputs import Inputs
from ghfdb.qc.uncertainty import UScore


class TestUScore:
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
