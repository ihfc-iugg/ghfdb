"""The field schema: a Frictionless Table Schema with the vocabulary values added.

The packaged ``schema.json`` is read by Frictionless. The facts the upload template
records that Table Schema has no property for, such as the published column name and
the obligation, stay in each field's ``custom`` dictionary.
"""

import json
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Self

from frictionless import Field, Schema
from rdflib import URIRef

from ghfdb.vocabularies import AllowedValue, MissingSchemeError, Vocabularies


def allowed_values(
    field: Field, vocabularies: Vocabularies
) -> tuple[AllowedValue, ...]:
    """Find the values a field accepts.

    Args:
        field: A field of the schema file.
        vocabularies: Where a vocabulary field takes its values from.

    Returns:
        The values of the field's controlled vocabulary, else the values written in
        the schema file, else an empty tuple for a free field.

    Raises:
        MissingSchemeError: The vocabularies lack the scheme or collection the field
            names. The message starts with the field's code.
    """
    vocabulary = field.custom["vocabulary"]
    if vocabulary is None:
        return tuple(
            AllowedValue(**value) for value in field.custom.get("allowedValues", ())
        )
    try:
        return vocabularies.allowed_values(vocabulary)
    except MissingSchemeError as error:
        raise MissingSchemeError(f"{field.name}: {error}") from error


@dataclass(frozen=True)
class FieldConcepts:
    """The concepts of one field that declarations name, and the terms they stand for.

    Attributes:
        terms: The term of each concept the field accepts, in the order of its allowed
            values.
        collections: The members of each collection named, nested collections
            included.
    """

    terms: Mapping[URIRef, str]
    collections: Mapping[URIRef, tuple[URIRef, ...]]

    @property
    def concepts(self) -> dict[str, URIRef]:
        """The concept of each term the field accepts."""
        return {term: concept for concept, term in self.terms.items()}

    def expand(self, references: Iterable[URIRef]) -> tuple[URIRef, ...]:
        """Replace each collection named by its members.

        Args:
            references: Concepts and collections of the field's scheme.

        Returns:
            The concepts, a collection giving its members in place.
        """
        return tuple(
            concept
            for reference in references
            for concept in self.collections.get(reference, (reference,))
        )

    def terms_for(self, references: Iterable[URIRef]) -> list[str]:
        """Give the terms the field accepts for concepts and collections.

        Args:
            references: Concepts and collections of the field's scheme.

        Returns:
            The term of each concept, a collection giving the terms of its members in
            place. A member the field does not accept has none.
        """
        return [
            self.terms[concept]
            for concept in self.expand(references)
            if concept in self.terms
        ]

    @staticmethod
    def merge(
        first: Mapping[str, "FieldConcepts"], second: Mapping[str, "FieldConcepts"]
    ) -> dict[str, "FieldConcepts"]:
        """Combine two resolutions.

        Args:
            first: The concepts of some fields.
            second: The concepts of some fields, resolved from the same schema.

        Returns:
            The concepts of every field of either, with the collections of both.
        """
        merged = dict(first)
        for code, found in second.items():
            known = merged.get(code)
            merged[code] = (
                found
                if known is None
                else FieldConcepts(
                    found.terms, {**known.collections, **found.collections}
                )
            )
        return merged

    @classmethod
    def resolve(
        cls,
        schema: Schema,
        references: Iterable[tuple[str, URIRef]],
        vocabularies: Vocabularies,
    ) -> dict[str, Self]:
        """Resolve the concepts and collections declarations name for their fields.

        Args:
            schema: The fields, which say where each takes its allowed values from.
            references: The code of a field and a concept or collection of its scheme,
                for everything the declarations name.
            vocabularies: Where the allowed values come from.

        Returns:
            For each field named, its concepts and the collections it was named with.

        Raises:
            MissingSchemeError: A reference is neither an allowed value of its field
                nor a collection of the field's scheme, or the field is not in the
                schema or has no vocabulary. The message names the field and the
                reference.
            OSError: The vocabularies are not cached and cannot be downloaded.
        """
        named: dict[str, dict[URIRef, None]] = {}
        for code, reference in references:
            named.setdefault(code, {})[reference] = None
        fields = {field.name: field for field in schema.fields}
        return {
            code: cls.of(code, fields.get(code), tuple(found), vocabularies)
            for code, found in named.items()
        }

    @classmethod
    def of(
        cls,
        code: str,
        field: Field | None,
        references: tuple[URIRef, ...],
        vocabularies: Vocabularies,
    ) -> Self:
        """Resolve the references to one field.

        Args:
            code: The field's code.
            field: The field, or None for a code the schema lacks.
            references: The concepts and collections named for the field.
            vocabularies: Where the allowed values come from.

        Returns:
            The field's concepts, with each collection named expanded.

        Raises:
            MissingSchemeError: As ``resolve`` says.
        """
        terms = {} if field is None else cls.terms_of(field, vocabularies)
        collections: dict[URIRef, tuple[URIRef, ...]] = {}
        for reference in references:
            if reference in terms:
                continue
            vocabulary = None if field is None else field.custom["vocabulary"]
            try:
                if vocabulary is None:
                    raise MissingSchemeError(f"{reference} has no vocabulary")
                graph = vocabularies.graph(
                    vocabulary["scheme"],
                    vocabulary.get("download"),
                    vocabulary.get("downloadFormat"),
                )
                members, ordered = Vocabularies.members(graph, reference)
            except MissingSchemeError:
                raise MissingSchemeError(
                    f"{code}: {reference} is neither an allowed value nor a "
                    "collection of the field's scheme"
                ) from None
            found = [URIRef(str(member)) for member in members]
            collections[reference] = tuple(
                found if ordered else sorted(found, key=cls.sort_key(terms))
            )
        return cls(terms, collections)

    @staticmethod
    def sort_key(terms: Mapping[URIRef, str]) -> Callable[[URIRef], str]:
        """Order concepts as the field lists them: by term, ignoring case.

        Args:
            terms: The term of each concept the field accepts.

        Returns:
            A sort key. A concept the field does not accept sorts by its URI.
        """
        return lambda concept: (
            terms[concept] if concept in terms else concept
        ).casefold()

    @staticmethod
    def terms_of(field: Field, vocabularies: Vocabularies) -> dict[URIRef, str]:
        """Map each concept a field accepts to its term.

        Args:
            field: A field of the schema.
            vocabularies: Where the allowed values come from.

        Returns:
            The term of each allowed value that belongs to a vocabulary.
        """
        return {
            URIRef(value.uri): value.term
            for value in allowed_values(field, vocabularies)
            if value.uri
        }


def load_schema(
    path: Path | None = None, vocabularies: Vocabularies | None = None
) -> Schema:
    """Read a schema file and give each vocabulary field its allowed values.

    Args:
        path: The file to read. Without one, the file packaged with ghfdb.
        vocabularies: Where the vocabulary files are kept. Without it, the cache
            directory, from which a missing file is downloaded.

    Returns:
        The schema, with an ``enum`` constraint on every field that has allowed
        values. The enum lives in memory only and is never written back to the file.

    Raises:
        MissingSchemeError: A scheme or collection a field names is not defined where
            it is published. The message starts with the field's code.
        OSError: A vocabulary file is not cached and cannot be downloaded.
    """
    if path is None:
        text = (
            resources.files("ghfdb.fields").joinpath("schema.json").read_text("utf-8")
        )
    else:
        text = path.read_text(encoding="utf-8")
    schema = Schema.from_descriptor(json.loads(text))
    files = Vocabularies() if vocabularies is None else vocabularies
    for field in schema.fields:
        if values := allowed_values(field, files):
            field.constraints["enum"] = [value.term for value in values]
    return schema


def field_for_column(schema: Schema, column_name: str) -> Field:
    """Find a field by the column name published in the upload template.

    Args:
        schema: The schema to search.
        column_name: A column name exactly as published, including its casing.

    Returns:
        The field.

    Raises:
        KeyError: If no field has that column name.
    """
    for field in schema.fields:
        if field.custom["columnName"] == column_name:
            return field
    raise KeyError(f"No field has the column name {column_name!r}")
