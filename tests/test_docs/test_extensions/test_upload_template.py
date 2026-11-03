from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from extensions.upload_template import replace_markers, template_name, write_template

import ghfdb
from ghfdb.fields import FieldSchema
from ghfdb.template import TemplateError, UploadTemplate


@pytest.fixture(scope="module")
def schema() -> FieldSchema:
    return FieldSchema.load()


class TestTemplateName:
    def test_names_the_file_for_the_package_version(self) -> None:
        assert template_name(ghfdb.__version__).endswith(f"{ghfdb.__version__}.xlsx")


class TestWriteTemplate:
    def test_writes_the_versioned_file_beside_the_page(self, tmp_path: Path) -> None:
        path = write_template(UploadTemplate(), tmp_path)

        assert path == tmp_path / "upload-template" / template_name(ghfdb.__version__)
        assert path.is_file()

    def test_content_equals_what_a_developer_writes(
        self,
        tmp_path: Path,
        workbook_content: Callable[[Path], dict[str, Any]],
    ) -> None:
        published = write_template(UploadTemplate(), tmp_path)
        developer = tmp_path / "developer.xlsx"
        UploadTemplate().write(developer)

        assert workbook_content(published) == workbook_content(developer)

    def test_replaces_the_file_of_an_earlier_build(self, tmp_path: Path) -> None:
        write_template(UploadTemplate(), tmp_path)

        path = write_template(UploadTemplate(), tmp_path)

        assert path.is_file()

    def test_a_generation_error_propagates(
        self, tmp_path: Path, schema: FieldSchema
    ) -> None:
        bound = next(field for field in schema if field.vocabulary is not None)
        emptied = replace(bound, allowed_values=())
        fields = tuple(emptied if f is bound else f for f in schema)
        template = UploadTemplate(FieldSchema(schema.path, schema.release, fields))

        with pytest.raises(TemplateError, match=bound.code):
            write_template(template, tmp_path)


class TestReplaceMarkers:
    def test_the_download_marker_becomes_a_download_link_to_the_versioned_file(
        self,
    ) -> None:
        name = template_name(ghfdb.__version__)

        text = replace_markers("Before\n\n{upload-template-download}\n\nAfter", name)

        assert f"{{download}}`{name} <{name}>`" in text
        assert "{upload-template-download}" not in text

    def test_a_page_without_markers_is_unchanged(self) -> None:
        text = "# A page\n\nMentions {upload-template-download} inline only.\n"

        assert replace_markers(text, "any.xlsx") == text
