import json
import re
from dataclasses import FrozenInstanceError, fields
from pathlib import Path
from typing import Any

import pytest
from frictionless import Schema
from openpyxl import load_workbook

from ghfdb.fields import (
    AllowedValue,
    FieldSchema,
    MissingSchemeError,
    UnknownFieldError,
    Vocabularies,
    VocabularyBinding,
)

COLOURS = "https://example.test/vocabularies/colours"
HERE = Path(__file__).parent
THREE_FIELDS = HERE / "schemas" / "three_fields.json"
TEST_VOCABULARIES = Vocabularies(HERE / "vocabularies")


def load_three_fields() -> FieldSchema:
    return FieldSchema.load(THREE_FIELDS, TEST_VOCABULARIES)


class TestVocabularyBinding:
    def test_has_exactly_the_planned_attributes(self) -> None:
        names = [field.name for field in fields(VocabularyBinding)]

        assert names == ["scheme", "collection", "term_form"]

    def test_is_frozen(self) -> None:
        binding = VocabularyBinding(COLOURS, None, "label")

        with pytest.raises(FrozenInstanceError):
            binding.scheme = "shapes"  # type: ignore[misc]


class TestAllowedValue:
    def test_has_exactly_the_planned_attributes(self) -> None:
        names = [field.name for field in fields(AllowedValue)]

        assert names == ["term", "label", "uri", "notation"]

    def test_is_frozen(self) -> None:
        value = AllowedValue("[Red]", "Red", "u:red", None)

        with pytest.raises(FrozenInstanceError):
            value.term = "[Blue]"  # type: ignore[misc]


class TestFieldSchema:
    def test_reads_fields_in_file_order(self) -> None:
        schema = load_three_fields()

        assert [field.code for field in schema] == ["X1", "X2", "X3"]
        assert schema.fields == tuple(schema)
        assert len(schema) == 3

    def test_reads_every_attribute_of_a_vocabulary_field(self) -> None:
        field = load_three_fields()["X1"]

        assert field.column_name == "shade"
        assert field.earlier_column_names == ("Shade_old",)
        assert field.group == "parent"
        assert field.name == "Shade"
        assert field.meaning == "The shade of a made-up thing."
        assert field.type == "string"
        assert field.decimal_places is None
        assert field.unit is None
        assert field.value_format is None
        assert field.obligation == "M"
        assert field.domain == ("B", "S")
        assert field.quality_relevance == "M-score"
        assert (field.minimum, field.maximum, field.max_length) == (None, None, None)
        assert field.separator == ";"
        assert field.guidance == "Pick one."
        assert field.sources == {
            "code": "upload-template",
            "columnName": "upload-template",
        }
        assert field.vocabulary == VocabularyBinding(
            COLOURS, f"{COLOURS}/warm", "label"
        )
        assert field.allowed_values == (
            AllowedValue("[Orange]", "Orange", f"{COLOURS}/orange", "or"),
            AllowedValue("[red]", "red", f"{COLOURS}/red", "rd"),
        )

    def test_reads_numeric_and_text_constraints(self) -> None:
        schema = load_three_fields()
        width, label = schema["X2"], schema["X3"]

        assert (width.decimal_places, width.unit) == (2, "mm")
        assert (width.minimum, width.maximum) == (0, 99.5)
        assert width.vocabulary is None
        assert width.allowed_values == ()
        assert (label.max_length, label.value_format) == (255, "YYYY-MM")
        assert (label.obligation, label.domain) == (None, ())

    def test_sources_cannot_be_changed(self) -> None:
        field = load_three_fields()["X2"]

        with pytest.raises(TypeError):
            field.sources["code"] = "x"  # type: ignore[index]

    def test_looks_up_by_code_or_published_column_name(self) -> None:
        schema = load_three_fields()

        assert schema["X2"] is schema["Width_mm"]
        assert schema["X2"].code == "X2"

    def test_column_name_casing_is_part_of_the_name(self) -> None:
        schema = load_three_fields()

        with pytest.raises(UnknownFieldError):
            schema["width_mm"]

    def test_earlier_column_names_are_not_lookup_keys(self) -> None:
        schema = load_three_fields()

        with pytest.raises(UnknownFieldError):
            schema["Shade_old"]

    def test_an_unknown_key_raises_an_error_naming_it(self) -> None:
        schema = load_three_fields()

        with pytest.raises(UnknownFieldError, match="nope") as caught:
            schema["nope"]
        assert isinstance(caught.value, KeyError)

    def test_loads_the_packaged_file_without_an_argument(self) -> None:
        schema = FieldSchema.load()

        assert len(schema) == 70

    def test_a_field_that_is_not_a_vocabulary_field_keeps_its_hand_written_values(
        self, tmp_path: Path
    ) -> None:
        data = json.loads(THREE_FIELDS.read_text())
        data["fields"][1]["allowedValues"] = [
            {"term": "[Yes]", "uri": None, "label": "Yes", "notation": None}
        ]
        path = tmp_path / "schema.json"
        path.write_text(json.dumps(data))

        field = FieldSchema.load(path, TEST_VOCABULARIES)["X2"]

        assert field.allowed_values == (AllowedValue("[Yes]", "Yes", None, None),)

    @pytest.mark.parametrize(
        ("key", "value", "missing"),
        [
            ("scheme", "https://example.test/other/colours", "other/colours"),
            ("collection", f"{COLOURS}/cool", "colours/cool"),
        ],
    )
    def test_a_name_the_vocabularies_do_not_define_is_reported_with_the_field(
        self, tmp_path: Path, key: str, value: str, missing: str
    ) -> None:
        data = json.loads(THREE_FIELDS.read_text())
        data["fields"][0]["vocabulary"][key] = value
        path = tmp_path / "schema.json"
        path.write_text(json.dumps(data))

        with pytest.raises(MissingSchemeError, match=f"X1.*{missing}"):
            FieldSchema.load(path, TEST_VOCABULARIES)


class TestDescriptor:
    def test_adds_an_enum_of_the_allowed_terms_to_a_vocabulary_field(self) -> None:
        schema = load_three_fields()

        entry = schema.descriptor()["fields"][0]

        assert entry["constraints"]["enum"] == ["[Orange]", "[red]"]

    def test_leaves_a_field_without_allowed_values_as_written(self) -> None:
        schema = load_three_fields()

        entry = schema.descriptor()["fields"][1]

        assert "enum" not in entry["constraints"]

    def test_never_changes_the_schema_it_is_built_from(self) -> None:
        schema = load_three_fields()

        schema.descriptor()

        assert "enum" not in schema.data["fields"][0]["constraints"]


ROOT = Path(__file__).parents[2]
SCHEMA_FILE = ROOT / "ghfdb" / "fields" / "schema.json"
TEMPLATE = ROOT / "tests" / "sources" / "upload-template.xlsx"
DECISIONS = ROOT / "specs" / "001-field-reference" / "decisions.md"

CODES = (
    [f"P{n}" for n in range(1, 14)]
    + [f"C{n}" for n in range(1, 50)]
    + [f"A{n}" for n in range(1, 9)]
)
SOURCE_KEYS = [
    "code",
    "columnName",
    "earlierColumnNames",
    "group",
    "name",
    "meaning",
    "type",
    "decimalPlaces",
    "maxLength",
    "unit",
    "valueFormat",
    "obligation",
    "domain",
    "qualityRelevance",
    "range",
    "vocabulary",
    "termForm",
    "allowedValues",
    "separator",
    "guidance",
]
SOURCE_CODES = {"upload-template", "fuchs-2023-appendix-a", "vocabularies"}
QUALITY = {"U score": "U-score", "M score": "M-score", "P Score": "perturbation flags"}
GROUPS = {"P": "parent", "C": "child", "A": "assessment"}
NUMBER = r"[\d,]+(?:\.\d+)?"
RANGE = re.compile(rf"^([-–]?)\s*({NUMBER})\s*[–-]\s*([+\-–]?)\s*({NUMBER})$")


def clean(value: object) -> str | None:
    """A template cell with its whitespace normalised and a dash read as empty."""
    if value is None:
        return None
    text = " ".join(str(value).split())
    return None if text in ("", "-") else text


def to_number(text: str) -> float:
    return float(text.replace(",", ""))


def parse_range(text: str) -> tuple[float, float]:
    match = RANGE.match(text)
    assert match, text
    low, high = to_number(match.group(2)), to_number(match.group(4))
    return (
        -low if match.group(1) else low,
        -high if match.group(3) in ("-", "–") else high,
    )


def read_template() -> dict[str, dict[str, str | None]]:
    sheet = load_workbook(TEMPLATE, read_only=True, data_only=True)["data list"]
    rows = [
        list(row) for row in sheet.iter_rows(min_row=1, max_row=8, values_only=True)
    ]
    names = [
        "code",
        "obligation",
        "domain",
        "quality",
        "name",
        "column",
        "unit",
        "range",
    ]
    return {
        str(rows[0][index]): {
            name: clean(row[index]) for name, row in zip(names, rows, strict=True)
        }
        for index in range(1, len(rows[0]))
    }


def load_entries() -> list[dict[str, Any]]:
    data = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
    entries: list[dict[str, Any]] = data["fields"]
    return entries


ENTRIES = {entry["name"]: entry for entry in load_entries()}
SHIPPED = FieldSchema.load()
DESCRIPTOR = {entry["name"]: entry for entry in SHIPPED.descriptor()["fields"]}
TEMPLATE_CELLS = read_template()
DECISION_IDS = set(re.findall(r"^### (D-\d+) ", DECISIONS.read_text(), re.MULTILINE))


class TestShippedSchemaShape:
    def test_has_the_seventy_fields_in_field_code_order(self) -> None:
        assert [entry["name"] for entry in load_entries()] == CODES

    def test_codes_and_column_names_are_unique(self) -> None:
        entries = load_entries()

        assert len({entry["name"] for entry in entries}) == len(entries)
        assert len({entry["columnName"] for entry in entries}) == len(entries)

    def test_the_only_missing_value_is_the_empty_cell(self) -> None:
        data = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))

        assert data["missingValues"] == [""]

    def test_is_in_the_form_the_serializer_writes(self) -> None:
        text = SCHEMA_FILE.read_text(encoding="utf-8")

        assert text == json.dumps(json.loads(text), indent=2, ensure_ascii=False) + "\n"

    def test_loads_through_the_public_class(self) -> None:
        schema = FieldSchema.load()

        assert [field.code for field in schema] == CODES

    def test_is_a_valid_table_schema(self) -> None:
        descriptor = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))

        report = Schema.validate_descriptor(descriptor)

        assert report.valid, report.flatten(["type", "note"])

    def test_the_complete_descriptor_is_a_valid_table_schema(self) -> None:
        report = Schema.validate_descriptor(FieldSchema.load().descriptor())

        assert report.valid, report.flatten(["type", "note"])

    def test_declares_no_release_version_or_doi(self) -> None:
        data = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))

        assert set(data) == {"missingValues", "fields"}

    def test_holds_no_enum_and_no_vocabulary_term(self) -> None:
        data = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))

        for entry in data["fields"]:
            assert "enum" not in entry["constraints"], entry["name"]
            if entry["vocabulary"] is not None:
                assert set(entry["vocabulary"]) == {
                    "scheme",
                    "collection",
                    "termForm",
                }, entry["name"]
                assert "allowedValues" not in entry, entry["name"]

    def test_vocabulary_fields_point_at_permanent_identifiers(self) -> None:
        data = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
        root = "https://w3id.org/ihfc-iugg/vocabularies/"

        for entry in data["fields"]:
            binding = entry["vocabulary"]
            if binding is None:
                continue
            assert binding["scheme"].startswith(root), entry["name"]
            if binding["collection"] is not None:
                assert binding["collection"].startswith(binding["scheme"] + "/")


@pytest.mark.parametrize("code", CODES)
class TestShippedField:
    def test_sources_have_exactly_the_planned_keys(self, code: str) -> None:
        assert sorted(ENTRIES[code]["sources"]) == sorted(SOURCE_KEYS)

    def test_every_source_is_known_and_every_decision_exists(self, code: str) -> None:
        for key in SOURCE_KEYS:
            source = ENTRIES[code]["sources"][key]
            if source.startswith("decision:"):
                assert source.removeprefix("decision:") in DECISION_IDS, (key, source)
            else:
                assert source in SOURCE_CODES, (key, source)

    def test_enum_of_the_descriptor_equals_the_allowed_terms(self, code: str) -> None:
        field = SHIPPED[code]
        enum = DESCRIPTOR[code]["constraints"].get("enum", [])

        assert enum == [value.term for value in field.allowed_values]

    def test_vocabulary_fields_have_allowed_values_with_uris(self, code: str) -> None:
        field = SHIPPED[code]

        if field.vocabulary is None:
            return
        assert field.allowed_values
        assert all(value.uri for value in field.allowed_values)

    def test_template_facts_equal_the_template(self, code: str) -> None:
        entry, cells = ENTRIES[code], TEMPLATE_CELLS[code]
        sources = entry["sources"]
        expected: dict[str, Any] = {
            "code": (cells["code"], entry["name"]),
            "columnName": (cells["column"], entry["columnName"]),
            "group": (GROUPS[code[0]], entry["group"]),
            "name": (cells["name"], entry["title"]),
            "unit": (cells["unit"], entry["unit"]),
            "obligation": (cells["obligation"], entry["obligation"]),
            "domain": (
                cells["domain"].split(",") if cells["domain"] else [],
                entry["domain"],
            ),
            "qualityRelevance": (
                QUALITY[cells["quality"]] if cells["quality"] else None,
                entry["qualityRelevance"],
            ),
        }
        for key, (cell, fact) in expected.items():
            if sources[key] == "upload-template":
                assert fact == cell, f"{code} {key}: {fact!r} against template {cell!r}"

    def test_range_equals_the_template(self, code: str) -> None:
        entry, cells = ENTRIES[code], TEMPLATE_CELLS[code]
        constraints = entry["constraints"]

        if entry["sources"]["range"] != "upload-template":
            return
        if entry["type"] in ("number", "integer") and cells["range"]:
            low, high = parse_range(cells["range"])
            assert (constraints["minimum"], constraints["maximum"]) == (low, high)
        else:
            assert "minimum" not in constraints
            assert "maximum" not in constraints


def date_pattern() -> str:
    field = ENTRIES["C38"]
    return str(field["constraints"]["pattern"])


class TestDateOfAcquisitionFormat:
    @pytest.mark.parametrize(
        "value", ["2005-01", "1998-12", "2005-01; 2007-12", "[Unspecified]"]
    )
    def test_a_month_a_range_of_months_or_unspecified_is_accepted(
        self, value: str
    ) -> None:
        assert re.fullmatch(date_pattern(), value)

    @pytest.mark.parametrize("value", ["2005", "2005-13", "2005-01;2007", "unknown"])
    def test_anything_else_is_refused(self, value: str) -> None:
        assert not re.fullmatch(date_pattern(), value)
