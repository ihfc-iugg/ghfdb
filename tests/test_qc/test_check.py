import difflib
from collections.abc import Callable
from typing import Any

import pandas
import pytest
from frictionless import Field, Schema

from ghfdb.qc.check import PROBLEM_COLUMNS, DatasetCheck, Kind

Children = Callable[..., pandas.DataFrame]


def found(frame: pandas.DataFrame, schema: Schema) -> set[tuple[int | None, str, Kind]]:
    problems = DatasetCheck(frame, schema).problems().to_dict("records")
    return {
        (None if pandas.isna(p["row"]) else p["row"], p["code"], p["kind"])
        for p in problems
    }


class TestProblemsFrame:
    def test_a_valid_child_has_no_problems(
        self, schema: Schema, children: Children
    ) -> None:
        problems = DatasetCheck(children({}), schema).problems()

        assert problems.empty
        assert list(problems.columns) == PROBLEM_COLUMNS

    def test_a_problem_carries_row_code_column_name_and_the_value_as_found(
        self, schema: Schema, children: Children, number_field: Field
    ) -> None:
        frame = children({number_field.name: " 1,234.5 "})

        problems = DatasetCheck(frame, schema).problems()

        (problem,) = problems.to_dict("records")
        assert problem["row"] == 9
        assert problem["code"] == number_field.name
        assert problem["column_name"] == number_field.custom["columnName"]
        assert problem["value"] == " 1,234.5 "
        assert pandas.isna(problem["suggestion"])

    def test_problems_come_by_row_and_then_by_the_order_of_the_fields(
        self,
        schema: Schema,
        children: Children,
        number_field: Field,
        length_field: Field,
    ) -> None:
        too_long = "x" * (length_field.constraints["maxLength"] + 1)
        frame = children(
            {number_field.name: "abc", length_field.name: too_long},
            {number_field.name: "abc"},
        )

        problems = DatasetCheck(frame, schema).problems()

        order = {field.name: i for i, field in enumerate(schema.fields)}
        records = problems.to_dict("records")
        keys = [(p["row"], order[p["code"]]) for p in records]
        assert keys == sorted(keys)
        assert [p["row"] for p in records] == [9, 9, 10]


class TestMissing:
    def test_an_empty_mandatory_field_is_missing(
        self, schema: Schema, children: Children, mandatory_field: Field
    ) -> None:
        frame = children({mandatory_field.name: None}, {mandatory_field.name: "  "})

        assert found(frame, schema) == {
            (9, mandatory_field.name, Kind.MISSING),
            (10, mandatory_field.name, Kind.MISSING),
        }

    def test_an_empty_recommended_field_is_not_missing(
        self, schema: Schema, children: Children, recommended_field: Field
    ) -> None:
        frame = children({recommended_field.name: None})

        assert found(frame, schema) == set()

    def test_an_empty_field_mandatory_in_one_domain_only_is_not_missing(
        self, schema: Schema, children: Children, one_domain_mandatory_field: Field
    ) -> None:
        frame = children({one_domain_mandatory_field.name: None})

        assert found(frame, schema) == set()


class TestWrongType:
    def test_text_that_is_not_a_number_is_wrong_type_and_never_out_of_range(
        self, schema: Schema, children: Children, number_field: Field
    ) -> None:
        texts = ["1,234.5", "12,5", "true", "abc", "1 2"]
        frame = children(*({number_field.name: text} for text in texts))

        problems = found(frame, schema)

        assert problems == {
            (9 + i, number_field.name, Kind.WRONG_TYPE) for i in range(len(texts))
        }

    def test_a_number_stored_as_text_is_accepted(
        self, schema: Schema, children: Children, number_field: Field
    ) -> None:
        low = number_field.constraints["minimum"]
        frame = children(
            {number_field.name: f"  {low}  "}, {number_field.name: f"{low}e0"}
        )

        assert found(frame, schema) == set()

    def test_a_fraction_in_a_whole_number_field_is_wrong_type(
        self, schema: Schema, children: Children, integer_field: Field
    ) -> None:
        low = integer_field.constraints["minimum"]
        frame = children(
            {integer_field.name: f"{low}.5"}, {integer_field.name: f"{low}.0"}
        )

        assert found(frame, schema) == {(9, integer_field.name, Kind.WRONG_TYPE)}

    def test_a_number_in_a_free_text_field_is_text(
        self, schema: Schema, children: Children, length_field: Field
    ) -> None:
        frame = children({length_field.name: "12.5"})

        assert found(frame, schema) == set()

    def test_a_date_in_a_year_and_month_field_is_wrong_type(
        self, schema: Schema, children: Children, pattern_field: Field
    ) -> None:
        frame = children({pattern_field.name: "2020-05-01 00:00:00"})

        assert found(frame, schema) == {(9, pattern_field.name, Kind.WRONG_TYPE)}


class TestOutOfRange:
    def test_a_number_beyond_either_end_of_its_range_is_out_of_range(
        self, schema: Schema, children: Children, number_field: Field
    ) -> None:
        low, high = (number_field.constraints[k] for k in ("minimum", "maximum"))
        frame = children(
            {number_field.name: low - 1},
            {number_field.name: high + 1},
            {number_field.name: low},
            {number_field.name: high},
        )

        assert found(frame, schema) == {
            (9, number_field.name, Kind.OUT_OF_RANGE),
            (10, number_field.name, Kind.OUT_OF_RANGE),
        }

    def test_text_longer_than_the_maximum_length_is_out_of_range(
        self, schema: Schema, children: Children, length_field: Field
    ) -> None:
        longest = length_field.constraints["maxLength"]
        frame = children(
            {length_field.name: "x" * (longest + 1)},
            {length_field.name: "x" * longest},
        )

        assert found(frame, schema) == {(9, length_field.name, Kind.OUT_OF_RANGE)}


class TestNotInVocabulary:
    def test_a_value_that_is_not_a_term_is_not_in_vocabulary(
        self, schema: Schema, children: Children, vocabulary_field: Field
    ) -> None:
        terms = vocabulary_field.constraints["enum"]
        frame = children(
            {vocabulary_field.name: "no such term at all"},
            {vocabulary_field.name: terms[-1]},
        )

        assert found(frame, schema) == {
            (9, vocabulary_field.name, Kind.NOT_IN_VOCABULARY)
        }


class TestNotANumber:
    @pytest.mark.parametrize("text", ["nan", "NaN", "inf", "-inf", "Infinity"])
    def test_a_ranged_number_field_gives_one_wrong_type_problem(
        self, schema: Schema, children: Children, number_field: Field, text: str
    ) -> None:
        frame = children({number_field.name: text})

        problems = DatasetCheck(frame, schema).problems()

        assert len(problems) == 1
        assert found(frame, schema) == {(9, number_field.name, Kind.WRONG_TYPE)}

    @pytest.mark.parametrize("text", ["nan", "inf", "-inf"])
    def test_a_number_field_without_a_range_gives_one_wrong_type_problem(
        self, schema: Schema, children: Children, number_field: Field, text: str
    ) -> None:
        descriptor = schema.to_descriptor()
        for field in descriptor["fields"]:
            if field["name"] == number_field.name:
                field["constraints"] = {}
        unranged = Schema.from_descriptor(descriptor)
        frame = children({number_field.name: text})

        problems = DatasetCheck(frame, unranged).problems()

        assert len(problems) == 1
        assert found(frame, unranged) == {(9, number_field.name, Kind.WRONG_TYPE)}


class TestNoColumn:
    def test_an_absent_mandatory_field_is_one_no_column_problem_and_missing_everywhere(
        self, schema: Schema, children: Children, mandatory_field: Field
    ) -> None:
        frame = children({}, {}, {}).drop(columns=mandatory_field.name)

        problems = DatasetCheck(frame, schema).problems()

        no_column = problems[problems["kind"] == Kind.NO_COLUMN]
        assert list(no_column["code"]) == [mandatory_field.name]
        assert no_column["row"].isna().all()
        assert found(frame, schema) == {
            (None, mandatory_field.name, Kind.NO_COLUMN),
            *((row, mandatory_field.name, Kind.MISSING) for row in (9, 10, 11)),
        }

    def test_an_absent_recommended_field_is_only_a_no_column_problem(
        self, schema: Schema, children: Children, recommended_field: Field
    ) -> None:
        frame = children({}, {}).drop(columns=recommended_field.name)

        assert found(frame, schema) == {(None, recommended_field.name, Kind.NO_COLUMN)}

    def test_the_no_column_problem_comes_before_the_problems_of_the_children(
        self,
        schema: Schema,
        children: Children,
        recommended_field: Field,
        number_field: Field,
    ) -> None:
        frame = children({number_field.name: "abc"}).drop(
            columns=recommended_field.name
        )

        problems = DatasetCheck(frame, schema).problems()

        assert list(problems["kind"]) == [Kind.NO_COLUMN, Kind.WRONG_TYPE]


class TestSuggestions:
    def suggested(
        self, schema: Schema, children: Children, field: Field, *values: str
    ) -> list[Any]:
        frame = children(*({field.name: value} for value in values))
        problems = DatasetCheck(frame, schema).problems()
        return [None if pandas.isna(s) else s for s in problems["suggestion"]]

    def test_a_value_missing_its_brackets_gets_the_term(
        self, schema: Schema, children: Children, vocabulary_field: Field
    ) -> None:
        term = vocabulary_field.constraints["enum"][0]

        found_ = self.suggested(schema, children, vocabulary_field, term.strip("[]"))

        assert found_ == [term]

    def test_a_value_in_another_case_gets_the_term(
        self, schema: Schema, children: Children, vocabulary_field: Field
    ) -> None:
        term = vocabulary_field.constraints["enum"][0]
        other = term.swapcase()
        assert other not in vocabulary_field.constraints["enum"]

        found_ = self.suggested(schema, children, vocabulary_field, other)

        assert found_ == [term]

    def test_a_slightly_misspelt_value_gets_the_term(
        self, schema: Schema, children: Children, vocabulary_field: Field
    ) -> None:
        term = max(vocabulary_field.constraints["enum"], key=len)
        inside = term.strip("[]")
        misspelt = f"[{inside[:-3]}{inside[-2]}{inside[-3]}{inside[-1]}]"
        assert misspelt not in vocabulary_field.constraints["enum"]

        found_ = self.suggested(schema, children, vocabulary_field, misspelt)

        assert found_ == [term]

    def test_a_value_close_to_no_term_gets_no_suggestion(
        self, schema: Schema, children: Children, vocabulary_field: Field
    ) -> None:
        found_ = self.suggested(schema, children, vocabulary_field, "qzxj wvkp 0000")

        assert found_ == [None]

    def test_a_value_repeated_on_many_children_is_matched_once(
        self,
        monkeypatch: pytest.MonkeyPatch,
        schema: Schema,
        children: Children,
        vocabulary_field: Field,
    ) -> None:
        calls = []
        real = difflib.get_close_matches

        def counting(*args: Any, **kwargs: Any) -> list[str]:
            calls.append(args)
            return real(*args, **kwargs)

        monkeypatch.setattr("ghfdb.qc.check.difflib.get_close_matches", counting)
        term = max(vocabulary_field.constraints["enum"], key=len)
        misspelt = term.strip("[]")[:-1] + "q"

        found_ = self.suggested(schema, children, vocabulary_field, *[misspelt] * 30)

        assert found_ == [term] * 30
        assert len(calls) == 1


def with_separator(schema: Schema, field: Field) -> Schema:
    """Copy a schema, making a field take several values in a cell."""
    descriptor = schema.to_descriptor()
    for described in descriptor["fields"]:
        if described["name"] == field.name:
            described["separator"] = ";"
    return Schema.from_descriptor(descriptor)


class TestSeveralValuesInACell:
    def test_no_packaged_field_has_a_separator_together_with_terms_or_a_pattern(
        self, schema: Schema
    ) -> None:
        both = [
            field.name
            for field in schema.fields
            if field.custom["separator"]
            and ({"enum", "pattern"} & set(field.constraints))
        ]

        assert both == []

    def test_each_term_in_a_cell_is_checked_on_its_own(
        self, schema: Schema, children: Children, vocabulary_field: Field
    ) -> None:
        first, second = vocabulary_field.constraints["enum"][:2]
        separated = with_separator(schema, vocabulary_field)
        frame = children(
            {vocabulary_field.name: f"{first};{second}"},
            {vocabulary_field.name: f"{first}; {second}"},
        )

        assert found(frame, separated) == set()

    def test_a_bad_term_is_a_problem_naming_that_term_and_its_row(
        self, schema: Schema, children: Children, vocabulary_field: Field
    ) -> None:
        term = vocabulary_field.constraints["enum"][0]
        separated = with_separator(schema, vocabulary_field)
        frame = children(
            {vocabulary_field.name: term},
            {vocabulary_field.name: f"{term}; nonsense one ; nonsense two"},
        )

        problems = DatasetCheck(frame, separated).problems()

        assert [(p["row"], p["value"]) for p in problems.to_dict("records")] == [
            (10, "nonsense one"),
            (10, "nonsense two"),
        ]
        assert set(problems["kind"]) == {Kind.NOT_IN_VOCABULARY}

    def test_each_value_in_a_cell_is_matched_to_the_pattern_on_its_own(
        self, schema: Schema, children: Children, pattern_field: Field
    ) -> None:
        separated = with_separator(schema, pattern_field)
        frame = children(
            {pattern_field.name: "2020-05; 2021-06"},
            {pattern_field.name: "2020-05; 2021-6"},
        )

        problems = DatasetCheck(frame, separated).problems().to_dict("records")

        assert [(p["row"], p["kind"], p["value"]) for p in problems] == [
            (10, Kind.WRONG_TYPE, "2021-6")
        ]

    def test_a_field_without_a_separator_takes_the_whole_cell_as_one_value(
        self, schema: Schema, children: Children, vocabulary_field: Field
    ) -> None:
        terms = vocabulary_field.constraints["enum"]
        frame = children({vocabulary_field.name: f"{terms[0]};{terms[1]}"})

        assert found(frame, schema) == {
            (9, vocabulary_field.name, Kind.NOT_IN_VOCABULARY)
        }
