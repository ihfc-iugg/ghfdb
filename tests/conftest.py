from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
import responses
from frictionless import Schema
from openpyxl import load_workbook

from ghfdb.fields import Vocabularies, caching_session, load_schema


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
# from an earlier run.
@pytest.fixture(scope="session")
def published_vocabularies(tmp_path_factory: pytest.TempPathFactory) -> Vocabularies:
    return Vocabularies(caching_session(tmp_path_factory.mktemp("vocabularies")))


@pytest.fixture(scope="session")
def schema(published_vocabularies: Vocabularies) -> Schema:
    return load_schema(vocabularies=published_vocabularies)


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
