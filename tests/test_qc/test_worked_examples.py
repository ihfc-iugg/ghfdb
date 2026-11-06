import json
import re
from collections.abc import Mapping
from importlib import resources
from typing import Any

import pytest
from frictionless import Schema

from ghfdb.fields import Vocabularies, allowed_values

# The parts whose inputs are not the fields of one child: the M-score takes two
# scores and a parent takes the codes of its children.
FIELD_PARTS = {
    "routing",
    "u-score",
    "probe-t",
    "probe-tc",
    "borehole-t",
    "borehole-tc",
    "perturbation-flags",
    "child",
}
FLAGS = re.compile("".join(f"[{letter}{letter.lower()}Xx\\-]" for letter in "SETPVCR"))
SCORE_RANGE = (0.1, 1.2)
U_SCORES = {"U1", "U2", "U3", "U4", "Ux"}
M_SCORES = {"M1", "M2", "M3", "M4", "M1x", "M2x", "M3x", "M4x", "Mx"}


@pytest.fixture(scope="module")
def document() -> Mapping[str, Any]:
    text = (resources.files("ghfdb.qc") / "worked_examples.json").read_text("utf-8")
    parsed: Mapping[str, Any] = json.loads(text)
    return parsed


@pytest.fixture(scope="module")
def examples(document: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    found: list[Mapping[str, Any]] = document["examples"]
    return found


def field_examples(examples: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [example for example in examples if example["part"] in FIELD_PARTS]


class TestIdentity:
    def test_every_example_has_its_own_identifier(
        self, examples: list[Mapping[str, Any]]
    ) -> None:
        identifiers = [example["id"] for example in examples]

        assert len(identifiers) == len(set(identifiers))

    def test_every_example_names_the_portal_test_that_asserts_it(
        self, examples: list[Mapping[str, Any]]
    ) -> None:
        for example in examples:
            assert example["portal_tests"], example["id"]
            for test in example["portal_tests"]:
                path, separator, name = test.partition("::")
                assert path.startswith("tests/") and separator and name, example["id"]


class TestInputs:
    def test_every_input_is_a_field_of_the_schema(
        self, schema: Schema, examples: list[Mapping[str, Any]]
    ) -> None:
        for example in field_examples(examples):
            assert set(example["inputs"]) <= set(schema.field_names), example["id"]

    def test_every_term_is_an_allowed_value_of_its_field(
        self,
        schema: Schema,
        published_vocabularies: Vocabularies,
        examples: list[Mapping[str, Any]],
    ) -> None:
        for example in field_examples(examples):
            for code, value in example["inputs"].items():
                field = schema.get_field(code)
                if field.custom["vocabulary"] is None:
                    continue
                allowed = {
                    allowed.term
                    for allowed in allowed_values(field, published_vocabularies)
                }
                given = value if isinstance(value, list) else [value]
                assert set(given) <= allowed, (example["id"], code)

    def test_a_parent_example_gives_each_child_a_quality_code(
        self, examples: list[Mapping[str, Any]]
    ) -> None:
        for example in examples:
            if example["part"] != "inheritance":
                continue
            for child in example["inputs"]["children"]:
                assert child["code"].count(".") == 2, example["id"]
                assert set(child) <= {"code", "C9"}, example["id"]


class TestExpected:
    def test_a_quality_code_is_its_three_parts_joined_by_full_stops(
        self, examples: list[Mapping[str, Any]]
    ) -> None:
        for example in examples:
            expected = example["expected"]
            if "code" in expected and {"U", "M", "flags"} <= set(expected):
                joined = f"{expected['U']}.{expected['M']}.{expected['flags']}"
                assert expected["code"] == joined, example["id"]

    def test_the_grades_and_flags_are_written_as_the_scheme_writes_them(
        self, examples: list[Mapping[str, Any]]
    ) -> None:
        for example in examples:
            expected = example["expected"]
            assert expected.get("U", "U1") in U_SCORES, example["id"]
            assert expected.get("M", "M1") in M_SCORES, example["id"]
            if "flags" in expected:
                assert FLAGS.fullmatch(expected["flags"]), example["id"]

    def test_a_score_is_a_number_in_range_or_null_when_not_determined(
        self, examples: list[Mapping[str, Any]]
    ) -> None:
        for example in examples:
            expected = example["expected"]
            scores = [expected.get("T"), expected.get("TC")]
            scores += list(expected.get("measurement", {}).values())
            for score in scores:
                assert score is None or SCORE_RANGE[0] <= score <= SCORE_RANGE[1], (
                    example["id"]
                )


class TestCriteria:
    def test_every_criterion_an_example_names_is_declared(
        self, document: Mapping[str, Any], examples: list[Mapping[str, Any]]
    ) -> None:
        named = {criterion for example in examples for criterion in example["criteria"]}

        assert named <= set(document["criteria"])

    def test_every_declared_criterion_has_an_example(
        self, document: Mapping[str, Any], examples: list[Mapping[str, Any]]
    ) -> None:
        named = {criterion for example in examples for criterion in example["criteria"]}

        assert set(document["criteria"]) - named == set()
