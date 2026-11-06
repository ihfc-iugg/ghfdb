from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from extensions.field_reference import FieldReference
from extensions.quality_scheme import SchemeReference
from frictionless import Schema

NOT_DETERMINED = "not determined"


def rows_of(markdown: str) -> list[list[str]]:
    """Return the cells of each body row of a Markdown table."""
    rows = [
        [cell.strip() for cell in line.strip().strip("|").split(" | ")]
        for line in markdown.splitlines()
        if line.startswith("|")
    ]
    return rows[2:]


def example(**changes: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "T-1",
        "part": "probe-t",
        "title": "Penetration 12 m",
        "inputs": {"C6": 12, "C12": "[Tilt corrected]"},
        "expected": {"T": 1.2, "marked": False},
        "portal_tests": ["tests/test_one.py::TestOne::test_it[12-1.2]"],
        "criteria": ["probe-t.penetration"],
    }
    return base | changes


def reference_of(schema: Schema, *examples: Mapping[str, Any]) -> SchemeReference:
    data = {
        "criteria": {"probe-t.penetration": "Probe penetration"},
        "examples": examples,
    }
    return SchemeReference(schema, data)


class TestFieldTable:
    def test_each_field_is_linked_with_its_column_name_and_name_from_the_schema(
        self, schema: Schema
    ) -> None:
        reference = reference_of(schema)

        rows = rows_of(reference.fields("C6", "C31"))

        assert [row[0] for row in rows] == [
            "{ref}`C6 <field-c6>`",
            "{ref}`C31 <field-c31>`",
        ]
        for row, code in zip(rows, ("C6", "C31"), strict=True):
            field = schema.get_field(code)
            assert row[1] == FieldReference.code(field.custom["columnName"])
            assert row[2] == FieldReference.cell(str(field.title))

    def test_the_legend_lists_the_fields_the_examples_give_in_field_code_order(
        self, schema: Schema
    ) -> None:
        reference = reference_of(
            schema, example(inputs={"C23": 5}), example(id="T-2", inputs={"C6": 1})
        )

        rows = rows_of(reference.field_legend())

        assert [row[0] for row in rows] == [
            "{ref}`C6 <field-c6>`",
            "{ref}`C23 <field-c23>`",
        ]


class TestExampleTable:
    def test_a_part_has_a_row_for_each_of_its_examples_and_none_for_another_part(
        self, schema: Schema
    ) -> None:
        reference = reference_of(
            schema, example(), example(id="T-2"), example(id="U-1", part="u-score")
        )

        rows = rows_of(reference.examples("probe-t"))

        assert [row[0] for row in rows] == ["`T-1`", "`T-2`"]

    def test_the_inputs_are_field_codes_with_terms_kept_verbatim(
        self, schema: Schema
    ) -> None:
        reference = reference_of(schema, example(inputs={"C6": 12, "C12": "[Tilt]"}))

        row = rows_of(reference.examples("probe-t"))[0]

        assert row[2] == "`C6` = 12, `C12` = `[Tilt]`"

    def test_an_empty_input_set_reads_as_a_dash(self, schema: Schema) -> None:
        reference = reference_of(schema, example(inputs={}))

        assert rows_of(reference.examples("probe-t"))[0][2] == "—"

    def test_several_values_of_a_field_are_listed(self, schema: Schema) -> None:
        reference = reference_of(schema, example(inputs={"C31": ["[BHT]", "[cBHT]"]}))

        assert (
            rows_of(reference.examples("probe-t"))[0][2] == "`C31` = `[BHT]`, `[cBHT]`"
        )

    def test_a_score_that_is_not_determined_is_never_written_as_a_number(
        self, schema: Schema
    ) -> None:
        reference = reference_of(
            schema, example(expected={"T": None, "TC": None, "M": "Mx"})
        )

        row = rows_of(reference.examples("probe-t"))[0]

        assert (
            row[3]
            == f"T-score {NOT_DETERMINED}, TC-score {NOT_DETERMINED}, M-score `Mx`"
        )

    @pytest.mark.parametrize(
        ("marked", "wording"), [(True, "missing-information mark"), (False, "no mark")]
    )
    def test_the_mark_is_stated_whether_or_not_it_is_set(
        self, schema: Schema, marked: bool, wording: str
    ) -> None:
        reference = reference_of(schema, example(expected={"T": 0.9, "marked": marked}))

        assert rows_of(reference.examples("probe-t"))[0][3] == f"T-score 0.9, {wording}"

    def test_the_own_scores_of_the_measurements_are_stated_beside_the_child_scores(
        self, schema: Schema
    ) -> None:
        expected = {"T": 1.2, "measurement": {"T": 1.0, "TC": None}}
        reference = reference_of(schema, example(expected=expected))

        row = rows_of(reference.examples("probe-t"))[0]

        assert row[3] == (
            f"T-score 1.2, own scores T-score 1.0, TC-score {NOT_DETERMINED}"
        )

    def test_a_measurement_scored_on_its_own_says_its_score_is_its_own(
        self, schema: Schema
    ) -> None:
        reference = reference_of(
            schema, example(scoring="measurement", expected={"TC": 0.8, "marked": True})
        )

        row = rows_of(reference.examples("probe-t"))[0]

        assert row[3] == "own TC-score 0.8, missing-information mark"

    def test_each_portal_test_is_linked_to_its_file_on_github(
        self, schema: Schema
    ) -> None:
        reference = reference_of(schema, example())

        row = rows_of(reference.examples("probe-t"))[0]

        assert row[4] == (
            "[`TestOne::test_it[12-1.2]`]"
            "(https://github.com/ihfc-iugg/ghfdb-portal/blob/main/tests/test_one.py)"
        )


class TestCoverage:
    def test_each_criterion_lists_how_many_examples_exercise_it(
        self, schema: Schema
    ) -> None:
        reference = reference_of(schema, example(), example(id="T-2"))

        rows = rows_of(reference.coverage())

        assert rows == [
            ["`probe-t.penetration`", "Probe penetration", "2: `T-1`, `T-2`"]
        ]


class TestRender:
    def test_a_call_in_a_page_is_replaced_by_the_table_it_stands_for(
        self, schema: Schema
    ) -> None:
        reference = reference_of(schema, example())

        page = reference.render('Fields:\n\n{{ fields("C6") }}\n')

        assert page == f"Fields:\n\n{reference.fields('C6')}\n"


class TestDecision:
    def test_a_decision_is_cited_by_its_heading_and_linked_to_it_on_github(
        self, schema: Schema
    ) -> None:
        citation = reference_of(schema).decision(1)

        assert citation == (
            "GHFDB portal decision [D1, “The toolbox, not the paper, is the "
            "definition”](https://github.com/ihfc-iugg/ghfdb-portal/blob/main/specs/"
            "007-quality-scores/decisions.md#d1--the-toolbox-not-the-paper-is-the-"
            "definition)"
        )

    def test_punctuation_in_a_heading_is_dropped_from_its_anchor_as_github_does(
        self, schema: Schema
    ) -> None:
        citation = reference_of(schema).decision(14)

        assert citation.endswith(
            "#d14--a-correction-recorded-as---is-unspecified-a-missing-one-is-empty)"
        )

    def test_a_decision_the_extension_does_not_know_is_refused(
        self, schema: Schema
    ) -> None:
        with pytest.raises(KeyError):
            reference_of(schema).decision(4)


class TestWorkedExamplesPage:
    def test_the_page_renders_the_examples_of_every_part_in_the_file(
        self, schema: Schema
    ) -> None:
        page = (
            Path(__file__).parents[3]
            / "docs"
            / "reference"
            / "quality-scheme"
            / "worked-examples.md"
        ).read_text(encoding="utf-8")
        reference = SchemeReference(schema)

        parts = {example["part"] for example in reference.data["examples"]}

        for part in parts:
            assert f'{{{{ examples("{part}") }}}}' in page, part
