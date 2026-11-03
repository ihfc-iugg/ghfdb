"""The field schema: the facts the upload template records about each field."""

import json
from collections.abc import Iterator, Mapping
from copy import deepcopy
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal, Self

from ghfdb.fields.release import (
    AllowedValue,
    MissingSchemeError,
    ReleaseFiles,
    VocabularyBinding,
    VocabularyRelease,
)


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
    def from_json(cls, data: Mapping[str, Any], release: ReleaseFiles) -> Self:
        """Build a field from its entry in the schema file.

        Args:
            data: The decoded JSON object of one entry in ``fields``.
            release: The vocabulary release a vocabulary field takes its values from.

        Returns:
            The field, with the allowed values its vocabulary gives it.

        Raises:
            MissingSchemeError: The release lacks the scheme or collection the field
                names. The message starts with the field's code.
        """
        constraints = data["constraints"]
        entry = data["vocabulary"]
        binding = (
            None
            if entry is None
            else VocabularyBinding(
                entry["schemeName"], entry["collectionName"], entry["termForm"]
            )
        )
        try:
            allowed_values = (
                tuple(AllowedValue(**value) for value in data.get("allowedValues", ()))
                if binding is None
                else release.allowed_values(binding)
            )
        except MissingSchemeError as error:
            raise MissingSchemeError(f"{data['name']}: {error}") from error
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
            vocabulary=binding,
            allowed_values=allowed_values,
            separator=data["separator"],
            guidance=data["guidance"],
            sources=MappingProxyType(dict(data["sources"])),
        )


class UnknownFieldError(KeyError):
    """Raised for a field code or published column name the schema does not hold."""


class FieldSchema:
    """The fields of the upload template, read from a schema file.

    Attributes:
        release: The vocabulary release the allowed values come from.
        fields: Every field, in the order of the file.
        data: The schema file as written, without any allowed values from the
            vocabulary release.
    """

    def __init__(
        self,
        release: VocabularyRelease,
        fields: tuple[Field, ...],
        data: Mapping[str, Any],
    ) -> None:
        """Hold the fields and index them by code and by published column name.

        Args:
            release: The vocabulary release the allowed values come from.
            fields: Every field, in file order.
            data: The decoded schema file the fields were read from.
        """
        self.release = release
        self.fields = fields
        self.data = data
        self.index = {field.column_name: field for field in fields}
        self.index.update({field.code: field for field in fields})

    @classmethod
    def load(
        cls, path: Path | None = None, vocabularies: ReleaseFiles | None = None
    ) -> Self:
        """Read a schema file and resolve its vocabulary fields against the release.

        Args:
            path: The file to read. Without one, the file packaged with ghfdb.
            vocabularies: The files of the vocabulary release the schema names.
                Without them, the release is taken from the cache, and downloaded
                into it first when it is not there.

        Returns:
            The schema.

        Raises:
            MissingSchemeError: The release lacks a scheme or collection a field names.
            OSError: The release is not cached and cannot be downloaded.
        """
        if path is None:
            text = (
                resources.files("ghfdb.fields")
                .joinpath("schema.json")
                .read_text("utf-8")
            )
        else:
            text = path.read_text(encoding="utf-8")
        data = json.loads(text)
        release = VocabularyRelease(**data["vocabularyRelease"])
        files = ReleaseFiles.fetch(release) if vocabularies is None else vocabularies
        fields = tuple(Field.from_json(entry, files) for entry in data["fields"])
        return cls(release, fields, data)

    def descriptor(self) -> dict[str, Any]:
        """Build the complete Frictionless Table Schema.

        Returns:
            The schema file with an ``enum`` constraint added to every field that has
            allowed values. It is built on each call and never written back.
        """
        descriptor = deepcopy(dict(self.data))
        for entry, field in zip(descriptor["fields"], self.fields, strict=True):
            if field.allowed_values:
                terms = [value.term for value in field.allowed_values]
                entry["constraints"]["enum"] = terms
        return descriptor

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
