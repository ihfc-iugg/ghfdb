from collections.abc import Callable, Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest
import responses
from frictionless import Field, Schema
from openpyxl import load_workbook

from ghfdb.fields import Vocabularies, caching_session, load_schema
from ghfdb.template import FIRST_DATA_ROW, UploadTemplate


def read_content(path: Path) -> dict[str, Any]:
    """Read what a workbook holds, leaving out the timestamps that differ."""
    workbook = load_workbook(path)
    content: dict[str, Any] = {}
    for sheet in workbook:
        cells = {
            cell.coordinate: cell.value
            for row in sheet.iter_rows()
            for cell in row
            if cell.value is not None
        }
        validations = sorted(
            (
                str(validation.sqref),
                validation.type,
                validation.formula1,
                validation.showErrorMessage,
                validation.allow_blank,
            )
            for validation in sheet.data_validations.dataValidation
        )
        content[sheet.title] = {"cells": cells, "validations": validations}
    return content


@pytest.fixture
def workbook_content() -> Callable[[Path], dict[str, Any]]:
    return read_content


# Tests that read the published vocabularies start with an empty cache, in a temporary
# directory, so they always see the files as currently published and never a copy kept
# from an earlier run. The files sit where ghfdb keeps them inside a user cache
# directory, so `vocabularies_cached` can point ghfdb at that directory.
@pytest.fixture(scope="session")
def cache_directory(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("cache")


@pytest.fixture(scope="session")
def published_vocabularies(cache_directory: Path) -> Vocabularies:
    return Vocabularies(caching_session(cache_directory / "vocabularies"))


@pytest.fixture(scope="session")
def schema(published_vocabularies: Vocabularies) -> Schema:
    return load_schema(vocabularies=published_vocabularies)


@pytest.fixture
def vocabularies_cached(
    monkeypatch: pytest.MonkeyPatch, cache_directory: Path, schema: Schema
) -> Path:
    """Make ghfdb find the session's filled vocabulary cache, never the user's.

    Requesting the session schema fills the cache first, so nothing is downloaded
    afterwards.
    """
    monkeypatch.setattr(
        "ghfdb.fields.vocabularies.user_cache_dir", lambda _: str(cache_directory)
    )
    return cache_directory


def valid_value(field: Field) -> Any:
    """Build a value a field accepts, from the field's own constraints."""
    constraints = field.constraints
    if terms := constraints.get("enum"):
        return terms[0]
    if field.custom["valueFormat"] == "YYYY-MM":
        return "2020-05"
    if field.type in ("number", "integer"):
        return constraints.get("minimum", 1)
    return "text"


@pytest.fixture
def valid_child(schema: Schema) -> dict[str, Any]:
    """One child with a valid value in every field, keyed by field code."""
    return {field.name: valid_value(field) for field in schema.fields}


@pytest.fixture
def filled_workbook(
    schema: Schema, tmp_path: Path
) -> Callable[[Sequence[Mapping[str, Any]]], Path]:
    """Write a copy of the upload template with one child per mapping from row 9.

    Each mapping holds values by field code, and by ``ID`` for the first column.
    """

    def fill(children: Sequence[Mapping[str, Any]]) -> Path:
        path = tmp_path / "workbook.xlsx"
        UploadTemplate(schema).write(path)
        workbook = load_workbook(path)
        sheet = workbook["data list"]
        columns = {field.name: index + 2 for index, field in enumerate(schema.fields)}
        for row, child in enumerate(children, start=FIRST_DATA_ROW):
            for code, value in child.items():
                sheet.cell(row, 1 if code == "ID" else columns[code], value)
        workbook.save(path)
        return path

    return fill


@pytest.fixture
def without_allowed_values() -> Callable[[Schema, str], Schema]:
    """Copy a schema, taking the allowed values from one field."""

    def copy(schema: Schema, code: str) -> Schema:
        broken = Schema.from_descriptor(schema.to_descriptor())
        del broken.get_field(code).constraints["enum"]
        return broken

    return copy


@pytest.fixture
def web() -> Iterator[responses.RequestsMock]:
    """Stand in for the web, so that no test reaches the network by accident."""
    with responses.RequestsMock(assert_all_requests_are_fired=False) as mock:
        yield mock
