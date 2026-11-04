import json
import re
from dataclasses import FrozenInstanceError, fields
from pathlib import Path
from typing import Any

import pytest
from frictionless import Schema
from openpyxl import load_workbook

from ghfdb.fields.schema import (
    AllowedValue,
    FieldSchema,
    UnknownFieldError,
    VocabularyBinding,
    VocabularyRelease,
)

COLOURS = "https://example.test/vocabularies/colours"
THREE_FIELDS = Path(__file__).parent / "schemas" / "three_fields.json"


class TestVocabularyRelease:
    def test_holds_a_version_and_a_bare_doi(self) -> None:
        release = VocabularyRelease("9999.1", "10.0000/test.1")

        assert (release.version, release.doi) == ("9999.1", "10.0000/test.1")

    def test_is_frozen(self) -> None:
        release = VocabularyRelease("9999.1", "10.0000/test.1")

        with pytest.raises(FrozenInstanceError):
            release.version = "9999.2"  # type: ignore[misc]


class TestVocabularyBinding:
    def test_has_exactly_the_planned_attributes(self) -> None:
        names = [field.name for field in fields(VocabularyBinding)]

        assert names == [
            "scheme_name",
            "collection_name",
            "scheme",
            "collection",
            "term_form",
        ]

    def test_is_frozen(self) -> None:
        binding = VocabularyBinding("colours", None, "u:colours", None, "label")

        with pytest.raises(FrozenInstanceError):
            binding.scheme_name = "shapes"  # type: ignore[misc]


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
        schema = FieldSchema.load(THREE_FIELDS)

        assert [field.code for field in schema] == ["X1", "X2", "X3"]
        assert schema.fields == tuple(schema)
        assert len(schema) == 3

    def test_reads_the_release_and_the_path(self) -> None:
        schema = FieldSchema.load(THREE_FIELDS)

        assert schema.release == VocabularyRelease("9999.1", "10.0000/test.1")
        assert schema.path == THREE_FIELDS

    def test_reads_every_attribute_of_a_vocabulary_field(self) -> None:
        field = FieldSchema.load(THREE_FIELDS)["X1"]

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
            "colours",
            "warm",
            "https://example.test/vocabularies/colours",
            "https://example.test/vocabularies/colours/warm",
            "label",
        )
        assert field.allowed_values == (
            AllowedValue(
                "[Green]",
                "Green",
                f"{COLOURS}/green",
                None,
            ),
            AllowedValue("[Red]", "Red", f"{COLOURS}/red", "r"),
        )

    def test_reads_numeric_and_text_constraints(self) -> None:
        schema = FieldSchema.load(THREE_FIELDS)
        width, label = schema["X2"], schema["X3"]

        assert (width.decimal_places, width.unit) == (2, "mm")
        assert (width.minimum, width.maximum) == (0, 99.5)
        assert width.vocabulary is None
        assert width.allowed_values == ()
        assert (label.max_length, label.value_format) == (255, "YYYY-MM")
        assert (label.obligation, label.domain) == (None, ())

    def test_sources_cannot_be_changed(self) -> None:
        field = FieldSchema.load(THREE_FIELDS)["X2"]

        with pytest.raises(TypeError):
            field.sources["code"] = "x"  # type: ignore[index]

    def test_looks_up_by_code_or_published_column_name(self) -> None:
        schema = FieldSchema.load(THREE_FIELDS)

        assert schema["X2"] is schema["Width_mm"]
        assert schema["X2"].code == "X2"

    def test_column_name_casing_is_part_of_the_name(self) -> None:
        schema = FieldSchema.load(THREE_FIELDS)

        with pytest.raises(UnknownFieldError):
            schema["width_mm"]

    def test_earlier_column_names_are_not_lookup_keys(self) -> None:
        schema = FieldSchema.load(THREE_FIELDS)

        with pytest.raises(UnknownFieldError):
            schema["Shade_old"]

    def test_an_unknown_key_raises_an_error_naming_it(self) -> None:
        schema = FieldSchema.load(THREE_FIELDS)

        with pytest.raises(UnknownFieldError, match="nope") as caught:
            schema["nope"]
        assert isinstance(caught.value, KeyError)

    def test_loads_the_packaged_file_without_an_argument(self) -> None:
        schema = FieldSchema.load()

        assert schema.path.name == "schema.json"
        assert schema.release.version == "2026.1"


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
SOURCE_CODES = {"upload-template", "fuchs-2023-appendix-a", "vocabulary-release"}
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

    def test_enum_equals_the_allowed_terms(self, code: str) -> None:
        entry = ENTRIES[code]
        terms = [value["term"] for value in entry["allowedValues"]]

        assert entry["constraints"].get("enum", []) == terms

    def test_vocabulary_fields_have_uris_and_allowed_values(self, code: str) -> None:
        entry = ENTRIES[code]
        binding = entry["vocabulary"]

        if binding is None:
            return
        assert binding["scheme"].startswith("https://")
        assert entry["allowedValues"]
        assert all(value["uri"] for value in entry["allowedValues"])

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
    data = json.loads(FieldSchema.load().path.read_text())
    field = next(entry for entry in data["fields"] if entry["name"] == "C38")
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
