"""Render the quality scheme pages from the worked examples and the field schema."""

import json
from collections.abc import Mapping
from functools import cache
from importlib import resources
from pathlib import Path
from typing import Any

from frictionless import Schema
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from sphinx.application import Sphinx

from extensions.field_reference import FieldReference
from ghfdb.fields import Vocabularies, load_schema

TEMPLATES = Path(__file__).parent / "templates"
PAGES = "reference/quality-scheme/"
EXAMPLES = resources.files("ghfdb.qc") / "worked_examples.json"
PORTAL_TESTS = "https://github.com/ihfc-iugg/ghfdb-portal/blob/main/"

EXPECTED_LABELS = {
    "rules": "rules",
    "U": "U-score",
    "T": "T-score",
    "TC": "TC-score",
    "M": "M-score",
    "flags": "flags",
    "code": "quality code",
}
NOT_DETERMINED = "not determined"
MISSING = "—"


class SchemeReference:
    """Markdown for the quality scheme pages, rendered from the worked examples.

    The Markdown is written in ``templates/quality_scheme.md.jinja``. This class gives
    the template the schema and the examples, and writes each example's values.

    Args:
        schema: The field schema the examples' field codes belong to.
        examples: The parsed worked examples file. Without it, the packaged file.
    """

    def __init__(
        self, schema: Schema, examples: Mapping[str, Any] | None = None
    ) -> None:
        self.schema = schema
        self.data: Mapping[str, Any] = (
            json.loads(EXAMPLES.read_text(encoding="utf-8"))
            if examples is None
            else examples
        )
        self.environment = Environment(
            loader=FileSystemLoader(TEMPLATES),
            undefined=StrictUndefined,
            keep_trailing_newline=True,
        )
        self.environment.filters.update(
            cell=FieldReference.cell, code=FieldReference.code
        )
        self.macros: Any = self.environment.get_template(
            "quality_scheme.md.jinja"
        ).make_module(
            {
                "schema": schema,
                "examples_of": self.examples_of,
                "inputs": self.inputs,
                "expected": self.expected,
                "tests": self.tests,
                "criteria": self.data["criteria"],
                "covering": self.covering,
                "codes_used": self.codes_used,
            }
        )
        self.environment.globals.update(
            fields=self.fields,
            examples=self.examples,
            field_legend=self.field_legend,
            coverage=self.coverage,
        )

    def examples_of(self, part: str) -> list[Mapping[str, Any]]:
        """List the examples of one part of the scheme, in the file's order.

        Args:
            part: The ``part`` of the examples, such as ``probe-t``.

        Returns:
            The examples whose ``part`` it is.
        """
        return [e for e in self.data["examples"] if e["part"] == part]

    def covering(self, criterion: str) -> list[str]:
        """List the identifiers of the examples that exercise a criterion.

        Args:
            criterion: A key of the file's ``criteria``.

        Returns:
            The example identifiers, in the file's order.
        """
        return [e["id"] for e in self.data["examples"] if criterion in e["criteria"]]

    def codes_used(self) -> list[str]:
        """List the field codes any example gives, in field-code order.

        Returns:
            The codes, ordered as the field schema orders its fields.
        """
        used = {code for e in self.data["examples"] for code in e["inputs"]}
        return [name for name in self.schema.field_names if name in used]

    @staticmethod
    def value(value: Any) -> str:
        """Write one value of an example as a reader sees it.

        Args:
            value: A number, a term, a boolean, ``None`` or a list of these.

        Returns:
            Numbers and booleans as they are, terms in a code span, ``None`` as
            not determined and a list as its values separated by commas.
        """
        if value is None:
            return NOT_DETERMINED
        if isinstance(value, list):
            return ", ".join(SchemeReference.value(item) for item in value)
        if isinstance(value, bool):
            return str(value).lower()
        if isinstance(value, str):
            return FieldReference.code(value)
        return str(value)

    def inputs(self, example: Mapping[str, Any]) -> str:
        """Write an example's inputs, each as a field code and its value.

        Args:
            example: One example of the file.

        Returns:
            The inputs separated by commas, or a dash when there are none.
        """
        inputs: Mapping[str, Any] = example["inputs"]
        if not inputs:
            return MISSING
        return ", ".join(
            f"{FieldReference.code(key)} = {self.value(value)}"
            for key, value in inputs.items()
        )

    def expected(self, example: Mapping[str, Any]) -> str:
        """Write an example's expected values.

        Args:
            example: One example of the file.

        Returns:
            The expected values separated by commas, each named.
        """
        expected: Mapping[str, Any] = example["expected"]
        parts = [
            f"{label} {self.value(expected[key])}"
            for key, label in EXPECTED_LABELS.items()
            if key in expected
        ]
        if "marked" in expected:
            parts.append(
                "missing-information mark" if expected["marked"] else "no mark"
            )
        if "measurement" in expected:
            own = expected["measurement"]
            parts.append(
                f"own scores T-score {self.value(own['T'])}, "
                f"TC-score {self.value(own['TC'])}"
            )
        return ", ".join(parts)

    @staticmethod
    def tests(example: Mapping[str, Any]) -> str:
        """Link the GHFDB portal tests that assert an example.

        Args:
            example: One example of the file.

        Returns:
            One link per test to the test's file, each reading as the test's name.
        """
        links = []
        for test in example["portal_tests"]:
            path, _, name = test.partition("::")
            links.append(f"[{FieldReference.code(name)}]({PORTAL_TESTS}{path})")
        return " ".join(links)

    def fields(self, *codes: str) -> str:
        """Write the table of the fields a part of the scheme reads.

        Args:
            codes: The field codes, in the order to list them.

        Returns:
            A Markdown table with the code linked to its field entry, the published
            column name and the name of each field.
        """
        return str(self.macros.field_table(codes))

    def field_legend(self) -> str:
        """Write the table of every field the worked examples give.

        Returns:
            A Markdown table in field-code order.
        """
        return str(self.macros.field_table(self.codes_used()))

    def examples(self, part: str) -> str:
        """Write the table of one part's worked examples.

        Args:
            part: The ``part`` of the examples, such as ``probe-t``.

        Returns:
            A Markdown table with a row per example.
        """
        return str(self.macros.example_table(part))

    def coverage(self) -> str:
        """Write the table that lists the examples exercising each criterion.

        Returns:
            A Markdown table with a row per criterion.
        """
        return str(self.macros.coverage())

    def render(self, page: str) -> str:
        """Render a page whose source calls the functions of this class.

        Args:
            page: The raw source of a page.

        Returns:
            The page with each call replaced by the Markdown it stands for.
        """
        return self.environment.from_string(page).render()


@cache
def scheme_reference() -> SchemeReference:
    """Read the packaged field schema once for the whole build."""
    return SchemeReference(load_schema(vocabularies=Vocabularies()))


def source_read(app: Sphinx, docname: str, source: list[str]) -> None:
    """Render the quality scheme pages, which are templates."""
    if docname.startswith(PAGES):
        source[0] = scheme_reference().render(source[0])


def setup(app: Sphinx) -> dict[str, Any]:
    """Register the extension's handler.

    Args:
        app: The Sphinx application.

    Returns:
        The extension's metadata.
    """
    app.connect("source-read", source_read)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
