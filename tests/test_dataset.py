from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import pandas
import pytest
from frictionless import Schema

import ghfdb
import ghfdb.qc
from ghfdb.dataset import Dataset
from ghfdb.fields import Vocabularies
from ghfdb.qc.check import PROBLEM_COLUMNS, Kind
from ghfdb.qc.workbook import UploadWorkbook
from ghfdb.template import FIRST_DATA_ROW

Filler = Callable[[Sequence[Mapping[str, Any]]], Path]


class TestDataset:
    def test_holds_the_dataframe_it_is_given(self) -> None:
        frame = pandas.DataFrame({"P1": ["1"]})

        dataset = Dataset(frame)

        assert dataset.data is frame

    def test_is_exported_with_the_names_of_the_check(self) -> None:
        assert ghfdb.Dataset is Dataset
        assert ghfdb.qc.UploadWorkbook is UploadWorkbook
        assert ghfdb.qc.CheckError is ghfdb.qc.workbook.CheckError


class TestFromWorkbook:
    def test_holds_the_children_of_the_workbook(
        self, schema: Schema, filled_workbook: Filler, valid_child: dict[str, Any]
    ) -> None:
        path = filled_workbook([valid_child, valid_child])

        dataset = Dataset.from_workbook(path, schema)

        pandas.testing.assert_frame_equal(
            dataset.data, UploadWorkbook(path, schema).data()
        )
        assert len(dataset.data) == 2

    def test_reads_the_packaged_schema_without_one(
        self,
        vocabularies_cached: Path,
        schema: Schema,
        filled_workbook: Filler,
        valid_child: dict[str, Any],
    ) -> None:
        path = filled_workbook([valid_child])

        dataset = Dataset.from_workbook(path)

        assert list(dataset.data.columns) == [field.name for field in schema.fields]


class TestCheck:
    def test_gives_the_problems_found_in_the_children(
        self,
        vocabularies_cached: Path,
        schema: Schema,
        filled_workbook: Filler,
        valid_child: dict[str, Any],
    ) -> None:
        number = next(f for f in schema.fields if f.type == "number")
        path = filled_workbook([valid_child, valid_child | {number.name: "abc"}])
        dataset = Dataset.from_workbook(path, schema)

        problems = dataset.check(schema)

        assert {
            (p["row"], p["code"], p["kind"]) for p in problems.to_dict("records")
        } == {(FIRST_DATA_ROW + 1, number.name, Kind.WRONG_TYPE)}

    def test_writes_nothing_into_the_users_cache(
        self,
        vocabularies_cached: Path,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        schema: Schema,
        filled_workbook: Filler,
        valid_child: dict[str, Any],
    ) -> None:
        user = tmp_path / "user"
        user.mkdir()
        monkeypatch.setenv("XDG_CACHE_HOME", str(user))
        dataset = Dataset.from_workbook(filled_workbook([valid_child]), schema)

        dataset.check(schema)

        assert list(user.rglob("*")) == []

    def test_checks_against_the_packaged_schema_without_one(
        self,
        vocabularies_cached: Path,
        filled_workbook: Filler,
        valid_child: dict[str, Any],
    ) -> None:
        dataset = Dataset.from_workbook(filled_workbook([valid_child]))

        assert dataset.check().empty


class TestCheckRules:
    def test_applies_the_cross_field_rules_by_default(
        self,
        vocabularies_cached: Path,
        schema: Schema,
        filled_workbook: Filler,
        valid_child: dict[str, Any],
    ) -> None:
        path = filled_workbook([valid_child | {"P12": "[Drilling]", "C5": None}])
        dataset = Dataset.from_workbook(path, schema)

        problems = dataset.check(schema)

        assert [
            (p["row"], p["code"], p["kind"], p["rule"])
            for p in problems.to_dict("records")
        ] == [(FIRST_DATA_ROW, "C5", Kind.RULE, "CF-1")]

    def test_applies_no_rule_when_given_none(
        self,
        vocabularies_cached: Path,
        schema: Schema,
        filled_workbook: Filler,
        valid_child: dict[str, Any],
    ) -> None:
        path = filled_workbook([valid_child | {"P12": "[Drilling]", "C5": None}])
        dataset = Dataset.from_workbook(path, schema)

        assert dataset.check(schema, rules=()).empty


SCORE_COLUMNS = [
    "rules",
    "U",
    "T",
    "TC",
    "marked",
    "M",
    "flags",
    "code",
    "own_T",
    "own_TC",
    "own_T_marked",
    "own_TC_marked",
]
# A probing child that scores M1 without the mark.
PROBE = {
    "P12": "[Probing (offshore, ocean)]",
    "P6": "-3000",
    "C1": "80",
    "C2": "4",
    "C6": "12",
    "C23": "45",
    "C37": "6",
    "C41": "[In-situ probe]",
    "C42": "[Actual heat-flow location]",
    "C43": "[Probe - pulse technique]",
    "C44": "[Saturated measured in-situ]",
    "C45": "[Actual in-situ (pT) conditions]",
    "C47": "4",
}


def children(*cells: Mapping[str, Any]) -> pandas.DataFrame:
    """Build the children from their cells, indexed by Excel row from 9."""
    return pandas.DataFrame(
        list(cells),
        index=pandas.Index(range(9, 9 + len(cells)), name="row"),
        dtype=object,
    )


def problem_table(*problems: Mapping[str, Any]) -> pandas.DataFrame:
    """Build a problem table from the columns each problem sets."""
    return pandas.DataFrame(list(problems), columns=PROBLEM_COLUMNS)


class TestScores:
    def test_gives_one_row_per_child_under_its_own_index(
        self, published_vocabularies: Vocabularies
    ) -> None:
        data = children(PROBE, PROBE | {"P12": None}).rename(index={9: 12, 10: 9})

        scores = Dataset(data).scores(vocabularies=published_vocabularies)

        assert list(scores.columns) == SCORE_COLUMNS
        assert scores.index.tolist() == [12, 9]
        assert scores["rules"].tolist() == ["probe sensing", pandas.NA]

    def test_a_child_that_cannot_be_scored_shows_not_determined_never_zero(
        self, published_vocabularies: Vocabularies
    ) -> None:
        scores = Dataset(children({"C1": None})).scores(
            vocabularies=published_vocabularies
        )

        row = scores.iloc[0]
        assert row[["T", "TC", "marked", "own_T", "own_TC"]].isna().all()
        assert (row["U"], row["M"], row["code"]) == ("Ux", "Mx", "Ux.Mx.-------")

    def test_a_dataset_without_children_gives_an_empty_table_with_the_columns(
        self, published_vocabularies: Vocabularies
    ) -> None:
        data = pandas.DataFrame({"P12": [], "C1": []}, dtype=object)

        scores = Dataset(data).scores(vocabularies=published_vocabularies)

        assert scores.empty
        assert list(scores.columns) == SCORE_COLUMNS

    def test_a_term_the_field_does_not_allow_is_scored_as_empty(
        self, published_vocabularies: Vocabularies
    ) -> None:
        wrong = PROBE | {"C45": PROBE["C44"]}

        scored = Dataset(children(wrong)).scores(vocabularies=published_vocabularies)
        empty = Dataset(children(PROBE | {"C45": None})).scores(
            vocabularies=published_vocabularies
        )

        pandas.testing.assert_frame_equal(scored, empty)
        assert scored["marked"].iloc[0]


class TestScoresWithProblems:
    def test_a_cell_named_by_a_wrong_type_problem_is_scored_as_empty_and_marked(
        self, published_vocabularies: Vocabularies
    ) -> None:
        data = children(PROBE | {"C37": "2.5"})
        problems = problem_table(
            {"row": 9, "code": "C37", "kind": Kind.WRONG_TYPE, "value": "2.5"}
        )

        without = Dataset(data).scores(vocabularies=published_vocabularies)
        scored = Dataset(data).scores(problems, published_vocabularies)
        empty = Dataset(children(PROBE | {"C37": None})).scores(
            vocabularies=published_vocabularies
        )

        pandas.testing.assert_frame_equal(scored, empty)
        assert scored["marked"].iloc[0]
        assert not without["marked"].iloc[0]

    @pytest.mark.parametrize(
        "kind",
        [Kind.MISSING, Kind.OUT_OF_RANGE, Kind.NOT_IN_VOCABULARY],
    )
    def test_every_kind_that_names_a_cell_blanks_it(
        self, published_vocabularies: Vocabularies, kind: Kind
    ) -> None:
        data = children(PROBE)
        problems = problem_table({"row": 9, "code": "C37", "kind": kind})

        scored = Dataset(data).scores(problems, published_vocabularies)
        empty = Dataset(children(PROBE | {"C37": None})).scores(
            vocabularies=published_vocabularies
        )

        pandas.testing.assert_frame_equal(scored, empty)

    def test_a_rule_problem_blanks_the_field_in_code_and_not_the_one_in_related(
        self, published_vocabularies: Vocabularies
    ) -> None:
        problems = problem_table(
            {
                "row": 9,
                "code": "C37",
                "kind": Kind.RULE,
                "rule": "CF-1",
                "related": "P12 explo_method [Probing (offshore, ocean)]",
            }
        )

        scored = Dataset(children(PROBE)).scores(problems, published_vocabularies)
        empty = Dataset(children(PROBE | {"C37": None})).scores(
            vocabularies=published_vocabularies
        )

        pandas.testing.assert_frame_equal(scored, empty)
        assert scored["rules"].iloc[0] == "probe sensing"

    def test_a_column_problem_blanks_nothing(
        self, published_vocabularies: Vocabularies
    ) -> None:
        problems = problem_table(
            {"row": pandas.NA, "code": "C37", "kind": Kind.NO_COLUMN}
        )

        scored = Dataset(children(PROBE)).scores(problems, published_vocabularies)
        plain = Dataset(children(PROBE)).scores(vocabularies=published_vocabularies)

        pandas.testing.assert_frame_equal(scored, plain)

    def test_a_problem_names_the_child_by_its_index_and_leaves_the_others(
        self, published_vocabularies: Vocabularies
    ) -> None:
        data = children(PROBE, PROBE)
        problems = problem_table({"row": 10, "code": "C37", "kind": Kind.MISSING})

        scored = Dataset(data).scores(problems, published_vocabularies)

        assert scored["marked"].tolist() == [False, True]

    def test_an_out_of_range_tilt_scores_differently_with_and_without_its_problem(
        self, published_vocabularies: Vocabularies
    ) -> None:
        data = children(PROBE | {"C23": "-5"})
        problems = problem_table(
            {"row": 9, "code": "C23", "kind": Kind.OUT_OF_RANGE, "value": "-5"}
        )

        without = Dataset(data).scores(vocabularies=published_vocabularies)
        scored = Dataset(data).scores(problems, published_vocabularies)

        assert not without["marked"].iloc[0]
        assert scored["marked"].iloc[0]
        assert scored["M"].iloc[0] == without["M"].iloc[0] + "x"

    def test_does_not_change_the_data_it_holds(
        self, published_vocabularies: Vocabularies
    ) -> None:
        data = children(PROBE)
        problems = problem_table({"row": 9, "code": "C37", "kind": Kind.MISSING})

        Dataset(data).scores(problems, published_vocabularies)

        assert data.loc[9, "C37"] == "6"
