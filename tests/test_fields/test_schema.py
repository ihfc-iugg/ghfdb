from dataclasses import FrozenInstanceError, fields

import pytest

from ghfdb.fields.schema import AllowedValue, VocabularyBinding, VocabularyRelease


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
