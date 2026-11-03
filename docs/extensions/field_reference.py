"""Render the field reference from the field schema while the documentation builds."""

import re
import shutil
from pathlib import Path
from typing import Any

from sphinx.application import Sphinx

from ghfdb.fields import Field, FieldSchema

DECISIONS_URL = "https://github.com/ihfc-iugg/ghfdb/blob/main/specs/001-field-reference/decisions.md"
SCHEMA_COPY = Path("reference") / "fields" / "ghfdb-field-schema.json"
MISSING = "—"
INDEX_MARKER = re.compile(r"^\{field-index\}$", re.MULTILINE)
ENTRIES_MARKER = re.compile(
    r"^\{field-entries\} (parent|child|assessment)$", re.MULTILINE
)
OBLIGATIONS = {"M": "Mandatory (M)", "R": "Recommended (R)", "O": "Optional (O)"}
DOMAINS = {"B": "Borehole and mine (B)", "S": "Probe sensing (S)"}


class FieldReference:
    """Markdown for the field reference, generated from a field schema.

    Args:
        schema: The field schema to render.
    """

    def __init__(self, schema: FieldSchema) -> None:
        self.schema = schema

    def cell(self, text: str) -> str:
        """Escape text so it reads as plain text in a Markdown table cell.

        Args:
            text: The text as recorded in the schema.

        Returns:
            The text with Markdown's special characters escaped.
        """
        return re.sub(r"([\\`*_\[\]<>|])", r"\\\1", text)

    def code(self, text: str) -> str:
        """Write text as an inline code span, which keeps it exactly as given.

        Args:
            text: The text to keep verbatim.

        Returns:
            A code span long enough to contain any backticks in the text.
        """
        fence = "`" * (max(map(len, re.findall("`+", text)), default=0) + 1)
        return f"{fence}{text}{fence}"

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
        release = self.schema.release
        if key == "upload-template":
            return "Upload template"
        if key == "fuchs-2023-appendix-a":
            return "Fuchs et al. (2023), Appendix A"
        if key == "vocabulary-release":
            return (
                f"[IHFC Controlled Vocabularies v{release.version}]"
                f"(https://doi.org/{release.doi})"
            )
        if key.startswith("decision:"):
            return f"[Decision {key.removeprefix('decision:')}]({DECISIONS_URL})"
        raise ValueError(f"Unknown source {key!r}")

    def sources(self, field: Field, *keys: str) -> str:
        """Name the distinct sources behind the facts of one table row.

        Args:
            field: The field the facts belong to.
            *keys: The keys of ``field.sources`` for the facts in the row.

        Returns:
            The sources, each once, in the order the facts come.
        """
        distinct = dict.fromkeys(field.sources[key] for key in keys)
        return "; ".join(self.source(code) for code in distinct)

    def rows(self, field: Field) -> list[tuple[str, str, str]]:
        """Build the table rows of one entry, in the order of the field facts.

        Args:
            field: The field to describe.

        Returns:
            Rows of fact, value and source, all already Markdown.
        """
        column = self.code(field.column_name)
        column_keys = ["columnName"]
        if field.earlier_column_names:
            earlier = ", ".join(self.code(name) for name in field.earlier_column_names)
            column += f" (earlier spelling: {earlier})"
            column_keys.append("earlierColumnNames")
        type_text = self.cell(field.type)
        type_keys = ["type"]
        if field.decimal_places is not None:
            type_text += f", {field.decimal_places} decimal places"
            type_keys.append("decimalPlaces")
        if field.max_length is not None:
            type_text += f", up to {field.max_length} characters"
            type_keys.append("maxLength")
        obligation = OBLIGATIONS.get(field.obligation or "", MISSING)
        domain = ", ".join(DOMAINS[code] for code in field.domain) or MISSING
        rows = [
            ("Field code", self.code(field.code), self.sources(field, "code")),
            ("Published column name", column, self.sources(field, *column_keys)),
            ("Name", self.cell(field.name), self.sources(field, "name")),
            ("Meaning", self.cell(field.meaning), self.sources(field, "meaning")),
            ("Type", type_text, self.sources(field, *type_keys)),
            ("Unit", self.cell(field.unit or MISSING), self.sources(field, "unit")),
            ("Obligation", obligation, self.sources(field, "obligation")),
            ("Domain", domain, self.sources(field, "domain")),
            (
                "Quality relevance",
                self.cell(field.quality_relevance or MISSING),
                self.sources(field, "qualityRelevance"),
            ),
        ]
        if field.minimum is not None or field.maximum is not None:
            low = MISSING if field.minimum is None else str(field.minimum)
            high = MISSING if field.maximum is None else str(field.maximum)
            rows.append(("Range", f"{low} to {high}", self.sources(field, "range")))
        if field.value_format is not None:
            rows.append(
                (
                    "Format",
                    self.code(field.value_format),
                    self.sources(field, "valueFormat"),
                )
            )
        if field.allowed_values:
            count = len(field.allowed_values)
            rows.append(
                (
                    "Allowed values",
                    f"{count} values, listed below",
                    self.sources(field, "allowedValues"),
                )
            )
        return rows

    def after_table(self, field: Field) -> list[str]:
        """Write the paragraphs and lists that follow an entry's table.

        Args:
            field: The field to describe.

        Returns:
            Blocks of Markdown, in reading order.
        """
        blocks = []
        binding = field.vocabulary
        if binding is not None:
            release = self.schema.release
            where = f"the concept scheme <{binding.scheme}>"
            if binding.collection is not None:
                where += f", limited to the collection <{binding.collection}>"
            blocks.append(
                f"The allowed values come from {where}, in the "
                f"IHFC Controlled Vocabularies v{release.version} "
                f"([DOI {release.doi}](https://doi.org/{release.doi}))."
            )
        if field.allowed_values:
            items = []
            for value in field.allowed_values:
                term = self.code(value.term)
                items.append(f"- [{term}]({value.uri})" if value.uri else f"- {term}")
            blocks.append("\n".join(items))
        if field.separator is not None:
            blocks.append(
                "Several values may be given in one cell, separated by "
                f"{self.code(field.separator)}. "
                f"Source: {self.sources(field, 'separator')}."
            )
        if field.guidance is not None:
            blocks.append(
                f"Guidance: {self.cell(field.guidance)} "
                f"Source: {self.sources(field, 'guidance')}."
            )
        return blocks

    def entry(self, field: Field) -> str:
        """Write the entry of one field: two targets, a heading and its facts.

        Args:
            field: The field to describe.

        Returns:
            Markdown for the entry, with a heading one level below the page title.
        """
        heading = (
            f"{field.code} · {self.cell(field.column_name)} — {self.cell(field.name)}"
        )
        table = ["| Fact | Value | Source |", "|---|---|---|"]
        table += [
            f"| {fact} | {re.sub(r'(?<!\\)\|', r'\\|', value)} | {source} |"
            for fact, value, source in self.rows(field)
        ]
        blocks = [
            f"(field-{field.code.lower()})=\n"
            f"(field-{field.column_name.lower()})=\n"
            f"## {heading}",
            "\n".join(table),
            *self.after_table(field),
        ]
        return "\n\n".join(blocks)

    def entries(self, group: str) -> str:
        """Write the entries of every field in one group, in field-code order.

        Args:
            group: ``parent``, ``child`` or ``assessment``.

        Returns:
            Markdown for the group's entries.
        """
        return "\n\n".join(
            self.entry(field) for field in self.schema if field.group == group
        )

    def index(self) -> str:
        """Write the table that lists every field, each linked to its entry.

        Returns:
            A Markdown table with a row per field, in field-code order.
        """
        rows = ["| Field code | Published column name | Name |", "|---|---|---|"]
        for field in self.schema:
            code = f"{{ref}}`{field.code} <field-{field.code.lower()}>`"
            column = f"{{ref}}`{field.column_name} <field-{field.column_name.lower()}>`"
            rows.append(f"| {code} | {column} | {self.cell(field.name)} |")
        return "\n".join(rows)


def replace_markers(text: str, reference: FieldReference) -> str:
    """Replace each marker line in a page with the Markdown it stands for.

    Args:
        text: The raw source of a page.
        reference: The rendered field reference.

    Returns:
        The page with ``{field-index}`` and ``{field-entries} <group>`` lines replaced.
    """
    text = INDEX_MARKER.sub(lambda _: reference.index(), text)
    return ENTRIES_MARKER.sub(lambda match: reference.entries(match[1]), text)


def copy_schema(schema: FieldSchema, source_directory: Path) -> None:
    """Copy the schema file into the documentation source, for download.

    Args:
        schema: The schema whose file is copied.
        source_directory: The documentation source directory.
    """
    target = source_directory / SCHEMA_COPY
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(schema.path, target)


def builder_inited(app: Sphinx) -> None:
    """Copy the packaged schema file where the opening page links to it."""
    copy_schema(FieldSchema.load(), Path(app.srcdir))


def source_read(app: Sphinx, docname: str, source: list[str]) -> None:
    """Fill in the field reference markers of a page being read."""
    if "{field-" in source[0]:
        source[0] = replace_markers(source[0], FieldReference(FieldSchema.load()))


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
