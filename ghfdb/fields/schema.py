"""The field schema: a Frictionless Table Schema with the vocabulary values added.

The packaged ``schema.json`` is read by Frictionless. The facts the upload template
records that Table Schema has no property for, such as the published column name and
the obligation, stay in each field's ``custom`` dictionary.
"""

import json
from importlib import resources
from pathlib import Path

from frictionless import Field, Schema

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
