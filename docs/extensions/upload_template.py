"""Publish the upload template while the documentation builds."""

import re
from pathlib import Path
from typing import Any

from sphinx.application import Sphinx

import ghfdb
from ghfdb.template import UploadTemplate

PAGE_DIRECTORY = "upload-template"
DOWNLOAD_MARKER = re.compile(r"^\{upload-template-download\}$", re.MULTILINE)


def template_name(version: str) -> str:
    """Name the published template after the package version that generates it.

    Args:
        version: The ghfdb version.

    Returns:
        The file name, such as ``ghfdb-upload-template-1.2.3.xlsx``.
    """
    return f"ghfdb-upload-template-{version}.xlsx"


def write_template(template: UploadTemplate, source_directory: Path) -> Path:
    """Write the template beside the page that links it, replacing an earlier build's.

    Args:
        template: The template to write.
        source_directory: The documentation source directory.

    Returns:
        The path of the written file.

    Raises:
        TemplateError: The template cannot be generated. The build fails.
    """
    path = source_directory / PAGE_DIRECTORY / template_name(template.version)
    path.parent.mkdir(parents=True, exist_ok=True)
    template.write(path, replace=True)
    return path


def replace_markers(text: str, name: str) -> str:
    """Replace each marker line in a page with the Markdown it stands for.

    Args:
        text: The raw source of a page.
        name: The file name of the published template.

    Returns:
        The page with the ``{upload-template-download}`` line replaced.
    """
    return DOWNLOAD_MARKER.sub(lambda _: f"{{download}}`{name} <{name}>`", text)


def builder_inited(app: Sphinx) -> None:
    """Write the template where the page links to it."""
    write_template(UploadTemplate(), Path(app.srcdir))


def source_read(app: Sphinx, docname: str, source: list[str]) -> None:
    """Fill in the upload template markers of a page being read."""
    if "{upload-template-" in source[0]:
        source[0] = replace_markers(source[0], template_name(ghfdb.__version__))


def setup(app: Sphinx) -> dict[str, Any]:
    """Register the extension's two handlers.

    Args:
        app: The Sphinx application.

    Returns:
        The extension's metadata.
    """
    app.connect("builder-inited", builder_inited)
    app.connect("source-read", source_read)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
