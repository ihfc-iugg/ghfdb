import warnings
from pathlib import Path

import pytest
from openpyxl import Workbook, load_workbook

from ghfdb.fields import FieldSchema
from ghfdb.template import UploadTemplate

SOURCE = Path(__file__).parent / "sources" / "upload-template.xlsx"


@pytest.fixture(scope="module")
def schema() -> FieldSchema:
    return FieldSchema.load()


@pytest.fixture
def workbook(schema: FieldSchema) -> Workbook:
    return UploadTemplate(schema).workbook()


class TestWorkbookLayout:
    def test_has_three_sheets_in_order(self, workbook: Workbook) -> None:
        assert workbook.sheetnames == ["readme", "data list", "controlled vocabulary"]

    def test_header_row_is_id_then_every_code_in_schema_order(
        self,
        workbook: Workbook,
        schema: FieldSchema,
    ) -> None:
        sheet = workbook["data list"]

        header = [cell.value for cell in sheet[1]]

        assert header == ["ID", *(field.code for field in schema)]

    def test_matches_the_hand_maintained_template(self, workbook: Workbook) -> None:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=".*extension.*")
            source = load_workbook(SOURCE)
        expected = source["data list"]
        actual = workbook["data list"]

        assert workbook.sheetnames == source.sheetnames
        assert actual["A1"].value == expected["A1"].value
        assert [actual.cell(row, 1).value for row in range(2, 9)] == [
            expected.cell(row, 1).value for row in range(2, 9)
        ]
        assert actual.max_row == 8
        assert not any(cell.value is not None for cell in actual[9])
