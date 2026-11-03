import json
import re
from pathlib import Path
from typing import Any

import pytest
from frictionless import Schema
from openpyxl import load_workbook

from ghfdb.fields.schema import FieldSchema

ROOT = Path(__file__).parents[2]
SCHEMA_FILE = ROOT / "src" / "ghfdb" / "fields" / "schema.json"
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
