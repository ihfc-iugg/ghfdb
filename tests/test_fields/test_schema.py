import json
import re
from dataclasses import FrozenInstanceError, fields
from pathlib import Path
from typing import Any

import pytest
import responses
from example_site import publish
from frictionless import Schema
from openpyxl import load_workbook

from ghfdb.fields import (
    AllowedValue,
    MissingSchemeError,
    Vocabularies,
    allowed_values,
    caching_session,
    field_for_column,
    load_schema,
)

COLOURS = "https://example.test/vocabularies/colours"
HERE = Path(__file__).parent
THREE_FIELDS = HERE / "schemas" / "three_fields.json"


@pytest.fixture
def three_fields(web: responses.RequestsMock, tmp_path: Path) -> Schema:
    publish(web, "colours")
    return load_schema(THREE_FIELDS, Vocabularies(caching_session(tmp_path / "cache")))


def write_variant(tmp_path: Path, change: Any) -> Path:
    """Write the three fields with a change applied to the decoded file."""
    data = json.loads(THREE_FIELDS.read_text())
    change(data)
    path = tmp_path / "schema.json"
    path.write_text(json.dumps(data))
    return path


class TestAllowedValue:
    def test_has_exactly_the_planned_attributes(self) -> None:
        names = [field.name for field in fields(AllowedValue)]

        assert names == ["term", "label", "uri", "notation"]

    def test_is_frozen(self) -> None:
        value = AllowedValue("[Red]", "Red", "u:red", None)

        with pytest.raises(FrozenInstanceError):
            value.term = "[Blue]"  # type: ignore[misc]


class TestLoadSchema:
    def test_returns_a_frictionless_schema_with_the_fields_in_file_order(
        self, three_fields: Schema
    ) -> None:
        assert isinstance(three_fields, Schema)
        assert three_fields.field_names == ["X1", "X2", "X3"]

    def test_reads_the_table_schema_properties_of_a_field(
        self, three_fields: Schema
    ) -> None:
        field = three_fields.get_field("X1")

        assert field.title == "Shade"
        assert field.description == "The shade of a made-up thing."
        assert field.type == "string"

    def test_keeps_the_facts_table_schema_has_no_property_for_in_custom(
        self, three_fields: Schema
    ) -> None:
        field = three_fields.get_field("X1")

        assert field.custom["columnName"] == "shade"
        assert field.custom["earlierColumnNames"] == ["Shade_old"]
        assert field.custom["group"] == "parent"
        assert field.custom["obligation"] == "M"
        assert field.custom["domain"] == ["B", "S"]
        assert field.custom["qualityRelevance"] == "M-score"
        assert field.custom["separator"] == ";"
        assert field.custom["guidance"] == "Pick one."
        assert field.custom["sources"] == {
            "code": "upload-template",
            "columnName": "upload-template",
        }
        assert field.custom["vocabulary"] == {
            "scheme": COLOURS,
            "collection": f"{COLOURS}/warm",
            "termForm": "label",
        }

    def test_gives_a_vocabulary_field_an_enum_of_its_terms(
        self, three_fields: Schema
    ) -> None:
        assert three_fields.get_field("X1").constraints["enum"] == ["[Orange]", "[red]"]

    def test_reads_numeric_and_text_constraints(self, three_fields: Schema) -> None:
        width, label = three_fields.get_field("X2"), three_fields.get_field("X3")

        assert width.custom["decimalPlaces"] == 2
        assert width.custom["unit"] == "mm"
        assert width.constraints == {"minimum": 0, "maximum": 99.5}
        assert label.constraints == {"maxLength": 255}
        assert label.custom["valueFormat"] == "YYYY-MM"

    def test_loads_the_packaged_file_without_a_path(self, schema: Schema) -> None:
        assert len(schema.fields) == 74

    def test_a_field_that_is_not_a_vocabulary_field_keeps_its_hand_written_values(
        self, tmp_path: Path, three_fields: Schema
    ) -> None:
        def add(data: dict[str, Any]) -> None:
            data["fields"][1]["allowedValues"] = [
                {"term": "[Yes]", "uri": None, "label": "Yes", "notation": None}
            ]

        path = write_variant(tmp_path, add)
        schema = load_schema(path, Vocabularies(caching_session(tmp_path / "cache")))

        assert schema.get_field("X2").constraints["enum"] == ["[Yes]"]

    @pytest.mark.parametrize(
        ("key", "value", "missing"),
        [
            ("scheme", "https://example.test/other/colours", "other/colours"),
            ("collection", f"{COLOURS}/cool", "colours/cool"),
        ],
    )
    def test_a_name_the_vocabularies_do_not_define_is_reported_with_the_field(
        self,
        web: responses.RequestsMock,
        tmp_path: Path,
        key: str,
        value: str,
        missing: str,
    ) -> None:
        publish(web, "colours")
        publish(web, "colours", base="https://example.test/other")
        path = write_variant(
            tmp_path, lambda data: data["fields"][0]["vocabulary"].update({key: value})
        )

        with pytest.raises(MissingSchemeError, match=f"X1.*{missing}"):
            load_schema(path, Vocabularies(caching_session(tmp_path / "cache")))


class TestToDescriptor:
    def test_adds_an_enum_of_the_allowed_terms_to_a_vocabulary_field(
        self, three_fields: Schema
    ) -> None:
        entry = three_fields.to_descriptor()["fields"][0]

        assert entry["constraints"]["enum"] == ["[Orange]", "[red]"]

    def test_leaves_a_field_without_allowed_values_as_written(
        self, three_fields: Schema
    ) -> None:
        entry = three_fields.to_descriptor()["fields"][1]

        assert "enum" not in entry["constraints"]

    def test_keeps_the_custom_facts(self, three_fields: Schema) -> None:
        entry = three_fields.to_descriptor()["fields"][1]

        assert entry["columnName"] == "Width_mm"
        assert entry["sources"] == {"code": "upload-template"}


class TestAllowedValues:
    def test_a_vocabulary_field_gives_the_values_of_its_vocabulary(
        self, three_fields: Schema, tmp_path: Path
    ) -> None:
        values = allowed_values(
            three_fields.get_field("X1"), Vocabularies(caching_session(tmp_path))
        )

        assert values == (
            AllowedValue("[Orange]", "Orange", f"{COLOURS}/orange", "or"),
            AllowedValue("[red]", "red", f"{COLOURS}/red", "rd"),
        )

    def test_a_free_field_gives_none(
        self, three_fields: Schema, tmp_path: Path
    ) -> None:
        values = allowed_values(
            three_fields.get_field("X2"), Vocabularies(caching_session(tmp_path))
        )

        assert values == ()


class TestFieldForColumn:
    def test_finds_a_field_by_its_published_column_name(
        self, three_fields: Schema
    ) -> None:
        assert field_for_column(three_fields, "Width_mm") is three_fields.get_field(
            "X2"
        )

    def test_the_casing_of_the_column_name_is_part_of_the_name(
        self, three_fields: Schema
    ) -> None:
        with pytest.raises(KeyError):
            field_for_column(three_fields, "width_mm")

    def test_an_earlier_column_name_does_not_find_a_field(
        self, three_fields: Schema
    ) -> None:
        with pytest.raises(KeyError):
            field_for_column(three_fields, "Shade_old")

    def test_an_unknown_name_raises_an_error_naming_it(
        self, three_fields: Schema
    ) -> None:
        with pytest.raises(KeyError, match="nope"):
            field_for_column(three_fields, "nope")


ROOT = Path(__file__).parents[2]
SCHEMA_FILE = ROOT / "ghfdb" / "fields" / "schema.json"
TEMPLATE = ROOT / "tests" / "sources" / "upload-template.xlsx"
DECISIONS = ROOT / "specs" / "001-field-reference" / "decisions.md"

CODES = (
    [f"P{n}" for n in range(1, 14)]
    + [f"C{n}" for n in range(1, 39)]
    + [f"C{n}" for n in range(50, 54)]
    + [f"C{n}" for n in range(39, 50)]
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
SOURCE_CODES = {
    "upload-template",
    "fuchs-2023-appendix-a",
    "fuchs-2025-template-2026-03",
    "vocabularies",
}
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
    def test_has_the_seventy_four_fields_in_the_order_of_the_template(self) -> None:
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

    def test_loads_through_the_public_function(self, schema: Schema) -> None:
        assert schema.field_names == CODES

    def test_is_a_valid_table_schema(self) -> None:
        descriptor = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))

        report = Schema.validate_descriptor(descriptor)

        assert report.valid, report.flatten(["type", "note"])

    def test_the_complete_descriptor_is_a_valid_table_schema(
        self, schema: Schema
    ) -> None:
        report = Schema.validate_descriptor(schema.to_descriptor())

        assert report.valid, report.flatten(["type", "note"])

    def test_declares_no_release_version_or_doi(self) -> None:
        data = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))

        assert set(data) == {"missingValues", "fields"}

    def test_holds_no_enum_and_no_vocabulary_term(self) -> None:
        data = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))

        for entry in data["fields"]:
            assert "enum" not in entry["constraints"], entry["name"]
            if entry["vocabulary"] is not None:
                assert set(entry["vocabulary"]) - {"download", "downloadFormat"} == {
                    "scheme",
                    "collection",
                    "termForm",
                }, entry["name"]
                assert "allowedValues" not in entry, entry["name"]

    def test_vocabulary_fields_point_at_permanent_identifiers_or_name_their_download(
        self,
    ) -> None:
        data = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
        root = "https://w3id.org/ihfc-iugg/vocabularies/"

        for entry in data["fields"]:
            binding = entry["vocabulary"]
            if binding is None:
                continue
            if "download" in binding:
                assert binding["downloadFormat"], entry["name"]
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

    def test_enum_of_the_descriptor_equals_the_allowed_terms(
        self, schema: Schema, published_vocabularies: Vocabularies, code: str
    ) -> None:
        field = schema.get_field(code)
        enum = schema.to_descriptor()["fields"][CODES.index(code)]["constraints"].get(
            "enum", []
        )

        values = allowed_values(field, published_vocabularies)

        assert enum == [value.term for value in values]

    def test_vocabulary_fields_have_allowed_values_with_uris(
        self, schema: Schema, published_vocabularies: Vocabularies, code: str
    ) -> None:
        field = schema.get_field(code)

        if field.custom["vocabulary"] is None:
            return
        values = allowed_values(field, published_vocabularies)
        assert values
        assert all(value.uri for value in values)

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
        "value", ["2005-01", "1998-12", "2005-01; 2007-12", "[unspecified]"]
    )
    def test_a_month_a_range_of_months_or_unspecified_is_accepted(
        self, value: str
    ) -> None:
        assert re.fullmatch(date_pattern(), value)

    @pytest.mark.parametrize("value", ["2005", "2005-13", "2005-01;2007", "unknown"])
    def test_anything_else_is_refused(self, value: str) -> None:
        assert not re.fullmatch(date_pattern(), value)
