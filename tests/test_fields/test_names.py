import json
from importlib import resources
from pathlib import Path
from typing import Any

import ghfdb.fields.names
from ghfdb.fields import Field, load_schema
from ghfdb.fields.generate import FieldNames


def packaged_fields() -> list[dict[str, Any]]:
    text = resources.files("ghfdb.fields").joinpath("schema.json").read_text("utf-8")
    fields: list[dict[str, Any]] = json.loads(text)["fields"]
    return fields


class TestField:
    def test_a_member_is_named_by_column_name_and_holds_the_field_code(self) -> None:
        assert Field.tc_location.value == "C42"
        assert Field.T_top_mean.value == "C50"
        assert Field.name.value == "P3"

    def test_there_is_one_member_per_schema_field_in_schema_order(self) -> None:
        schema = load_schema()

        assert [member.name for member in Field] == [
            field.custom["columnName"] for field in schema.fields
        ]
        assert [member.value for member in Field] == [
            field.name for field in schema.fields
        ]

    def test_a_member_is_a_string_that_indexes_the_data(self) -> None:
        counts: dict[str, int] = {Field.explo_method: 1}

        assert counts["P12"] == 1


class TestFieldNames:
    def test_the_names_file_is_what_the_schema_generates(self) -> None:
        on_disk = Path(ghfdb.fields.names.__file__).read_text(encoding="utf-8")

        assert FieldNames.render(packaged_fields()) == on_disk

    def test_a_member_renamed_by_hand_makes_the_file_differ(self) -> None:
        on_disk = Path(ghfdb.fields.names.__file__).read_text(encoding="utf-8")

        assert FieldNames.render(packaged_fields()) != on_disk.replace(
            "tc_location", "tc_site"
        )

    def test_a_corrected_column_name_changes_its_member(self) -> None:
        fields = packaged_fields()
        fields[0]["columnName"] = "heat_flow"

        source = FieldNames.render(fields)

        assert 'heat_flow = "P1"' in source
        assert 'q = "P1"' not in source
