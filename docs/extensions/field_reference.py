"""Render the field reference from the field schema while the documentation builds."""

import re
from functools import cache
from pathlib import Path
from typing import Any

from frictionless import Field, Schema
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from sphinx.application import Sphinx

from ghfdb.fields import AllowedValue, Vocabularies, allowed_values, load_schema
from ghfdb.template import VOCABULARIES

DECISIONS_URL = "https://github.com/ihfc-iugg/ghfdb/blob/main/specs/001-field-reference/decisions.md"
SCHEMA_COPY = Path("reference") / "fields" / "ghfdb-field-schema.json"
TEMPLATES = Path(__file__).parent / "templates"
PAGES = "reference/fields/"


class FieldReference:
    """Markdown for the field reference, rendered from a field schema.

    The Markdown is written in ``templates/field_reference.md.jinja``. This class
    gives the templates the schema and the few things Markdown needs done in code.

    Args:
        schema: The field schema to render.
        vocabularies: Where the vocabulary fields take their allowed values from.
            Without it, the cache directory.
    """

    def __init__(
        self, schema: Schema, vocabularies: Vocabularies | None = None
    ) -> None:
        self.schema = schema
        self.vocabularies = Vocabularies() if vocabularies is None else vocabularies
        self.environment = Environment(
            loader=FileSystemLoader(TEMPLATES),
            undefined=StrictUndefined,
            keep_trailing_newline=True,
        )
        self.environment.filters.update(
            cell=self.cell, code=self.code, pipes=self.pipes
        )
        self.macros: Any = self.environment.get_template(
            "field_reference.md.jinja"
        ).make_module(
            {"schema": schema, "sources": self.sources, "allowed_values": self.values}
        )
        self.environment.globals.update(index=self.index, entries=self.entries)

    @staticmethod
    def cell(text: str) -> str:
        """Escape text so it reads as plain text in a Markdown table cell.

        Args:
            text: The text as recorded in the schema.

        Returns:
            The text with Markdown's special characters escaped.
        """
        return re.sub(r"([\\`*_\[\]<>|])", r"\\\1", text)

    @staticmethod
    def code(text: str) -> str:
        """Write text as an inline code span, which keeps it exactly as given.

        Args:
            text: The text to keep verbatim.

        Returns:
            A code span long enough to contain any backticks in the text.
        """
        fence = "`" * (max(map(len, re.findall("`+", text)), default=0) + 1)
        return f"{fence}{text}{fence}"

    @staticmethod
    def pipes(markdown: str) -> str:
        """Escape the pipes of Markdown that goes into a table cell.

        Args:
            markdown: Text already escaped or quoted for Markdown.

        Returns:
            The text with every pipe that is not already escaped escaped.
        """
        return re.sub(r"(?<!\\)\|", r"\\|", markdown)

    def values(self, field: Field) -> tuple[AllowedValue, ...]:
        """List the allowed values of a field with the concept each one comes from.

        Args:
            field: A field of the schema.

        Returns:
            The values, which carry the URI the enum of the field leaves out.
        """
        return allowed_values(field, self.vocabularies)

    def source(self, key: str) -> str:
        """Say where a fact came from, as a phrase a reader outside the project knows.

        Args:
            key: A source code from the schema, such as ``upload-template`` or
                ``decision:D-5``.

        Returns:
            Markdown naming the source, linked where it can be.

        Raises:
            ValueError: The schema holds a source code this page does not know.
        """
        if key == "upload-template":
            return "Upload template"
        if key == "fuchs-2023-appendix-a":
            return "Fuchs et al. (2023), Appendix A"
        if key == "vocabularies":
            return f"[IHFC Controlled Vocabularies]({VOCABULARIES})"
        if key.startswith("decision:"):
            return f"[Decision {key.removeprefix('decision:')}]({DECISIONS_URL})"
        raise ValueError(f"Unknown source {key!r}")

    def sources(self, field: Field, keys: list[str]) -> str:
        """Name the distinct sources behind the facts of one table row.

        Args:
            field: The field the facts belong to.
            keys: The keys of the field's ``sources`` for the facts in the row.

        Returns:
            The sources, each once, in the order the facts come.
        """
        distinct = dict.fromkeys(field.custom["sources"][key] for key in keys)
        return "; ".join(self.source(code) for code in distinct)

    def index(self) -> str:
        """Write the table that lists every field, each linked to its entry.

        Returns:
            A Markdown table with a row per field, in field-code order.
        """
        return str(self.macros.index())

    def entries(self, group: str) -> str:
        """Write the entries of every field in one group, in field-code order.

        Args:
            group: ``parent``, ``child`` or ``assessment``.

        Returns:
            Markdown for the group's entries.
        """
        return str(self.macros.entries(group))

    def render(self, page: str) -> str:
        """Render a page whose source calls ``index()`` or ``entries(group)``.

        Args:
            page: The raw source of a page.

        Returns:
            The page with each call replaced by the Markdown it stands for.
        """
        return self.environment.from_string(page).render()


@cache
def field_reference() -> FieldReference:
    """Read the packaged field schema once for the whole build."""
    vocabularies = Vocabularies()
    return FieldReference(load_schema(vocabularies=vocabularies), vocabularies)


def copy_schema(schema: Schema, source_directory: Path) -> None:
    """Write the complete schema into the documentation source, for download.

    The copy carries the allowed values of every vocabulary field, which the schema
    file in the package leaves to the vocabularies.

    Args:
        schema: The schema to write.
        source_directory: The documentation source directory.
    """
    target = source_directory / SCHEMA_COPY
    target.parent.mkdir(parents=True, exist_ok=True)
    schema.to_json(str(target))


def builder_inited(app: Sphinx) -> None:
    """Copy the packaged schema file where the opening page links to it."""
    copy_schema(field_reference().schema, Path(app.srcdir))


def source_read(app: Sphinx, docname: str, source: list[str]) -> None:
    """Render the field reference pages, which are templates."""
    if docname.startswith(PAGES):
        source[0] = field_reference().render(source[0])


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
