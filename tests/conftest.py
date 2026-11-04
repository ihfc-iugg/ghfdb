import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from openpyxl import load_workbook

# Tests always read the vocabularies as currently published, never a copy kept from an
# earlier run, so the cache of a test session starts empty. This runs when pytest loads
# this file, before any test module loads the shipped schema.
os.environ["GHFDB_VOCABULARY_CACHE"] = tempfile.mkdtemp(prefix="ghfdb-vocabularies-")


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
