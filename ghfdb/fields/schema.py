"""The field schema: the facts the upload template records about each field."""

import json
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal, Self


@dataclass(frozen=True)
class VocabularyRelease:
    """The release of the IHFC Controlled Vocabularies a schema was built from.

    Attributes:
        version: The release version, such as ``2026.1``.
        doi: The bare DOI of the release, without a resolver prefix.
    """

    version: str
    doi: str


@dataclass(frozen=True)
class VocabularyBinding:
    """The controlled vocabulary a field takes its values from.

    Attributes:
        scheme_name: The last segment of the concept scheme URI.
        collection_name: The last segment of the collection URI, or None when the
            field takes every concept of the scheme.
        scheme: The full URI of the concept scheme.
        collection: The full URI of the collection, or None.
        term_form: Whether a value is written as the concept's label or its notation.
    """

    scheme_name: str
    collection_name: str | None
    scheme: str
    collection: str | None
    term_form: Literal["label", "notation"]


@dataclass(frozen=True)
class AllowedValue:
    """One value a field accepts.

    Attributes:
        term: The value as written in the template, in square brackets.
        label: The English preferred label of the concept.
        uri: The concept URI, or None for a value that belongs to no vocabulary.
        notation: The concept's notation, or None when it has none.
    """

    term: str
    label: str
    uri: str | None
    notation: str | None


@dataclass(frozen=True)
class Field:
    """One field of the upload template and everything recorded about it.

    Attributes:
        code: The field code, such as ``C43``.
        column_name: The column name published in the upload template.
        earlier_column_names: Names the column had in earlier templates.
        group: Whether the field belongs to the parent, child or assessment table.
        name: The field's title.
        meaning: What the field holds.
        type: The Table Schema type of the value.
        decimal_places: The number of decimal places, or None.
        unit: The unit of the value, or None.
        value_format: The text format of the value, such as ``YYYY-MM``, or None.
        obligation: ``M`` (mandatory), ``R`` (recommended), ``O`` (optional), or
            None when the template does not say.
        domain: The data domains the field applies to.
        quality_relevance: How the field enters the quality score, or None.
        minimum: The smallest accepted value, or None.
        maximum: The largest accepted value, or None.
        max_length: The longest accepted text, or None.
        vocabulary: The controlled vocabulary the field draws on, or None.
        allowed_values: The values the field accepts, empty when it is free.
        separator: The separator between several values in one cell, or None.
        guidance: Advice on filling the field in, or None.
        sources: For each fact, the source it was taken from. Read only.
    """

    code: str
    column_name: str
    earlier_column_names: tuple[str, ...]
    group: Literal["parent", "child", "assessment"]
    name: str
    meaning: str
    type: str
    decimal_places: int | None
    unit: str | None
    value_format: str | None
    obligation: Literal["M", "R", "O"] | None
    domain: tuple[str, ...]
    quality_relevance: str | None
    minimum: float | None
    maximum: float | None
    max_length: int | None
    vocabulary: VocabularyBinding | None
    allowed_values: tuple[AllowedValue, ...]
    separator: str | None
    guidance: str | None
    sources: Mapping[str, str]

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> Self:
        """Build a field from its entry in the schema file.

        Args:
            data: The decoded JSON object of one entry in ``fields``.

        Returns:
            The field.
        """
        constraints = data["constraints"]
        binding = data["vocabulary"]
        return cls(
            code=data["name"],
            column_name=data["columnName"],
            earlier_column_names=tuple(data["earlierColumnNames"]),
            group=data["group"],
            name=data["title"],
            meaning=data["description"],
            type=data["type"],
            decimal_places=data["decimalPlaces"],
            unit=data["unit"],
            value_format=data["valueFormat"],
            obligation=data["obligation"],
            domain=tuple(data["domain"]),
            quality_relevance=data["qualityRelevance"],
            minimum=constraints.get("minimum"),
            maximum=constraints.get("maximum"),
            max_length=constraints.get("maxLength"),
            vocabulary=None
            if binding is None
            else VocabularyBinding(
                scheme_name=binding["schemeName"],
                collection_name=binding["collectionName"],
                scheme=binding["scheme"],
                collection=binding["collection"],
                term_form=binding["termForm"],
            ),
            allowed_values=tuple(
                AllowedValue(
                    term=value["term"],
                    label=value["label"],
                    uri=value["uri"],
                    notation=value["notation"],
                )
                for value in data["allowedValues"]
            ),
            separator=data["separator"],
            guidance=data["guidance"],
            sources=MappingProxyType(dict(data["sources"])),
        )


class UnknownFieldError(KeyError):
    """Raised for a field code or published column name the schema does not hold."""


class FieldSchema:
    """The fields of the upload template, read from a schema file.

    Attributes:
        path: The JSON file the schema was read from.
        release: The vocabulary release the allowed values come from.
        fields: Every field, in the order of the file.
    """

    def __init__(
        self, path: Path, release: VocabularyRelease, fields: tuple[Field, ...]
    ) -> None:
        """Hold the fields and index them by code and by published column name.

        Args:
            path: The JSON file the fields were read from.
            release: The vocabulary release the allowed values come from.
            fields: Every field, in file order.
        """
        self.path = path
        self.release = release
        self.fields = fields
        self.index = {field.column_name: field for field in fields}
        self.index.update({field.code: field for field in fields})

    @classmethod
    def load(cls, path: Path | None = None) -> Self:
        """Read a schema file.

        Args:
            path: The file to read. Without one, the file packaged with ghfdb.

        Returns:
            The schema.
        """
        if path is None:
            with resources.as_file(
                resources.files("ghfdb.fields").joinpath("schema.json")
            ) as packaged:
                return cls.load(packaged)
        data = json.loads(path.read_text(encoding="utf-8"))
        release = data["vocabularyRelease"]
        return cls(
            path,
            VocabularyRelease(release["version"], release["doi"]),
            tuple(Field.from_json(entry) for entry in data["fields"]),
        )

    def __getitem__(self, key: str) -> Field:
        """Find a field by its code or its published column name.

        Args:
            key: A field code such as ``C43``, or a column name exactly as
                published, including its casing.

        Returns:
            The field.

        Raises:
            UnknownFieldError: If no field has that code or column name.
        """
        try:
            return self.index[key]
        except KeyError:
            raise UnknownFieldError(
                f"No field has the code or column name {key!r}"
            ) from None

    def __iter__(self) -> Iterator[Field]:
        """Iterate the fields in file order."""
        return iter(self.fields)

    def __len__(self) -> int:
        """Count the fields."""
        return len(self.fields)
