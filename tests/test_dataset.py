from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import pandas
from frictionless import Schema

import ghfdb
import ghfdb.qc
from ghfdb.dataset import Dataset
from ghfdb.qc.check import Kind
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
        self, schema: Schema, filled_workbook: Filler, valid_child: dict[str, Any]
    ) -> None:
        number = next(f for f in schema.fields if f.type == "number")
        path = filled_workbook([valid_child, valid_child | {number.name: "abc"}])
        dataset = Dataset.from_workbook(path, schema)

        problems = dataset.check(schema)

        assert {
            (p["row"], p["code"], p["kind"]) for p in problems.to_dict("records")
        } == {(FIRST_DATA_ROW + 1, number.name, Kind.WRONG_TYPE)}

    def test_checks_against_the_packaged_schema_without_one(
        self,
        vocabularies_cached: Path,
        filled_workbook: Filler,
        valid_child: dict[str, Any],
    ) -> None:
        dataset = Dataset.from_workbook(filled_workbook([valid_child]))

        assert dataset.check().empty
