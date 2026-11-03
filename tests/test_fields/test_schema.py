from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest

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
