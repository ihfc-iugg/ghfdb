"""Render the quality scheme pages from the worked examples and the field schema."""

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from importlib import resources
from pathlib import Path
from typing import Any

from frictionless import Schema
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from sphinx.application import Sphinx

from extensions.field_reference import FieldReference
from ghfdb.fields import Field, Vocabularies, load_schema
from ghfdb.fields.cells import terms_by_name
from ghfdb.qc import borehole, probe
from ghfdb.qc.criteria import CRITERIA
from ghfdb.qc.penalties import (
    SCORE_DECIMALS,
    Bands,
    Cases,
    Classes,
    Criterion,
    Table,
)

TEMPLATES = Path(__file__).parent / "templates"
PAGES = "reference/quality-scheme/"
EXAMPLES = resources.files("ghfdb.qc") / "worked_examples.json"
PORTAL_TESTS = "https://github.com/ihfc-iugg/ghfdb-portal/blob/main/"
# The tests of this package, which are the only ones under this directory.
PACKAGE_TESTS = "https://github.com/ihfc-iugg/ghfdb/blob/main/"
PACKAGE_TEST_DIRECTORY = "tests/test_qc/"
DECISIONS_URL = f"{PORTAL_TESTS}specs/007-quality-scores/decisions.md"
# The headings of the GHFDB portal's quality-score decisions that the pages cite, as
# they read in the decisions file.
DECISIONS = {
    1: "The toolbox, not the paper, is the definition",
    2: "Uncorrected scores on the measurement, corrected scores on the child",
    3: "The uncorrected TC-score scores pT conditions alone",
    5: "The quality code is written with two full stops",
    6: "Heat refraction is R, and the flags follow the paper's figure order",
    7: "A product on a class boundary takes the better class",
    8: "Multi-valued fields take the poorest matching class",
    9: "Parent inheritance follows the toolbox, with one addition",
    10: "The paper's worked examples are not the conformance oracle",
    11: "The probe tilt correction is read from the temperature correction",
    12: "The toolbox's code is the oracle where its own tests disagree with it",
    13: "A borehole child with no in-situ correction takes the agreement penalty",
    14: "A correction recorded as `-` is unspecified, a missing one is empty",
    15: (
        "Four misspelled method tokens in the toolbox are read as the methods they name"
    ),
    16: "A borehole temperature method that fits no case is marked",
    17: "Measurements are routed by the site's exploration method",
}

EXPECTED_LABELS = {
    "rules": "rules",
    "U": "U-score",
    "T": "T-score",
    "TC": "TC-score",
    "M": "M-score",
    "flags": "flags",
    "code": "quality code",
}
OWN_SCORES = ("T", "TC")
NOT_DETERMINED = "not determined"
MISSING = "—"
MINUS = "−"
ANY = "any"
EMPTY = "Empty"
OTHER_VALUE = "Any other value"


@dataclass(frozen=True)
class ScoreRange:
    """The lowest and the highest score that a set of criteria allow.

    Attributes:
        criteria: The criteria.
        added_up: Whether the penalties of all the criteria are added to 1.0, as those
            of a TC-score are, or only one criterion applies, as one of the cases of a
            borehole gradient does.
        fixed: Scores a child can have besides, such as that of the interval depth
            gate.
    """

    criteria: tuple[Criterion[Any], ...]
    added_up: bool
    fixed: tuple[float, ...] = ()

    @staticmethod
    def best(table: Table) -> float:
        """Give the highest penalty of a table.

        Args:
            table: The table.

        Returns:
            The highest penalty of its bands, groups or rows.

        Raises:
            TypeError: The table is of a kind this class cannot read.
        """
        penalties: list[float]
        match table:
            case Bands() as bands:
                penalties = [band.value for band in bands.bands]
            case Classes() as classes:
                penalties = [group.penalty for group in classes.groups]
            case Cases() as cases:
                penalties = [case.penalty for case in cases.cases]
            case _:
                raise TypeError(f"{table}: no penalties to read")
        return max(penalties)

    def lowest(self) -> float:
        """Give the lowest score, with every criterion at its largest penalty."""
        penalties = [criterion.table.largest() for criterion in self.criteria]
        score = 1 + (sum(penalties) if self.added_up else min(penalties))
        return float(round(min((score, *self.fixed)), SCORE_DECIMALS))

    def highest(self) -> float:
        """Give the highest score, with every criterion at its best penalty."""
        penalties = [self.best(criterion.table) for criterion in self.criteria]
        score = 1 + (sum(penalties) if self.added_up else max(penalties))
        return float(round(max((score, *self.fixed)), SCORE_DECIMALS))


# The criteria whose penalties make up each score, which the pages state the range of.
RANGES = {
    "probe-t": ScoreRange(probe.T_CRITERIA, added_up=True),
    "probe-tc": ScoreRange(probe.TC_CRITERIA, added_up=True),
    "borehole-t": ScoreRange(borehole.T_CRITERIA, added_up=False),
    "borehole-tc": ScoreRange(
        borehole.TC_CRITERIA, added_up=True, fixed=(borehole.GATE_SCORE,)
    ),
}


@dataclass(frozen=True)
class TableText:
    """What a page writes for the table of one criterion.

    Attributes:
        headers: The heading of each column, the penalty last.
        rows: The cells of each row, written for Markdown.
        notes: Sentences that follow the table.
    """

    headers: list[str]
    rows: list[list[str]]
    notes: list[str]


class CriterionTable:
    """Write the penalty table of a criterion from its declaration.

    Args:
        schema: The field schema, which gives each field's title and unit.
        vocabularies: Where the allowed values come from, to write each concept as the
            term its field accepts.
    """

    def __init__(self, schema: Schema, vocabularies: Vocabularies) -> None:
        self.schema = schema
        self.vocabularies = vocabularies
        self.terms: dict[str, dict[str, str]] = {}

    def term(self, field: str, name: str) -> str:
        """Write a concept as the term its field accepts.

        Args:
            field: The field's code.
            name: The concept's local name.

        Returns:
            The term, as an inline code span.
        """
        if field not in self.terms:
            self.terms[field] = terms_by_name(self.schema, field, self.vocabularies)
        return FieldReference.code(self.terms[field][name])

    def title(self, field: str) -> str:
        """Name a field by its title, escaped for a Markdown table.

        Args:
            field: The field's code.

        Returns:
            The field's title.
        """
        return FieldReference.cell(str(self.schema.get_field(field).title))

    @staticmethod
    def penalty(value: float) -> str:
        """Write a penalty with its sign, as the pages write one.

        Args:
            value: The penalty.

        Returns:
            ``+0.1``, ``0`` or ``−0.1``.
        """
        if value == 0:
            return "0"
        return f"{value:+.1f}".replace("-", MINUS)

    @classmethod
    def outcome(cls, table: Table, marked: bool) -> str:
        """Write what an empty or unmatched value scores.

        Args:
            table: The table, whose largest penalty the value takes.
            marked: Whether the value sets the mark.

        Returns:
            The penalty, with ``, with the mark`` when it sets it.
        """
        written = cls.penalty(table.largest())
        return f"{written}, with the mark" if marked else written

    def terms_of(self, field: str, names: tuple[str, ...]) -> str:
        """Write concepts as the terms their field accepts.

        Args:
            field: The field's code.
            names: The concepts' local names.

        Returns:
            The terms, separated by commas.
        """
        return ", ".join(self.term(field, name) for name in names)

    @staticmethod
    def edge(number: float) -> str:
        """Write the edge of a band without a needless decimal point."""
        return f"{number:g}"

    def band_label(self, bands: Bands, index: int) -> str:
        """Say which numbers a band holds.

        Args:
            bands: The table.
            index: The position of the band, the highest first.

        Returns:
            For example ``More than 3, up to 10``.
        """
        band = bands.bands[index]
        higher = bands.bands[index - 1] if index else None
        lower = None
        if band.above is not None:
            lower = (
                f"{self.edge(band.above)} or more"
                if band.inclusive
                else f"More than {self.edge(band.above)}"
            )
        upper = None
        if higher is not None and higher.above is not None:
            upper = (
                f"below {self.edge(higher.above)}"
                if higher.inclusive
                else f"up to {self.edge(higher.above)}"
            )
        if lower and upper:
            return f"{lower}, {upper}"
        if lower:
            return lower
        if upper and higher is not None and higher.above is not None:
            edge = self.edge(higher.above)
            return f"Below {edge}" if higher.inclusive else f"{edge} or less"
        return "Any number"

    def bands(self, title: str, table: Bands) -> TableText:
        """Write a table of bands.

        Args:
            title: What the criterion scores, as the heading of the first column.
            table: A number against edges.

        Returns:
            The table, with the field the criterion is left out for as a note.
        """
        unit = self.schema.get_field(table.field).custom.get("unit")
        heading = FieldReference.cell(title) + (f" ({unit})" if unit else "")
        rows = [
            [self.band_label(table, index), self.penalty(band.value)]
            for index, band in enumerate(table.bands)
        ]
        rows.append([EMPTY, self.outcome(table, table.empty_marked)])
        if table.bands[-1].above is not None:
            rows.append([OTHER_VALUE, self.outcome(table, table.unmatched_marked)])
        notes = [
            f"Left out when {self.title(field)} is "
            f"{self.terms_of(field, tuple(concepts))}: "
            "the criterion then adds no penalty and no mark."
            for field, concepts in (table.left_out_when or {}).items()
        ]
        return TableText([heading, "Penalty"], rows, notes)

    def classes(self, table: Classes) -> TableText:
        """Write a table of groups of concepts.

        Args:
            table: A term against groups.

        Returns:
            The table.
        """
        field = table.fields[0]
        heading = " or ".join(self.title(code) for code in table.fields)
        rows = [
            [self.terms_of(field, group.concepts), self.penalty(group.penalty)]
            for group in table.groups
        ]
        rows.append([EMPTY, self.outcome(table, table.empty_marked)])
        rows.append([OTHER_VALUE, self.outcome(table, table.unmatched_marked)])
        notes = (
            [f"An empty value is left out when another of {heading} is filled."]
            if table.skip_empty
            else []
        )
        return TableText([heading, "Penalty"], rows, notes)

    def cases(self, table: Cases) -> TableText:
        """Write a table of rows of conditions.

        Args:
            table: Rows of conditions on fields.

        Returns:
            The table, a column for each field its rows name.
        """
        fields = [Field(code) for code in table.reads()]
        rows = []
        for case in table.cases:
            cells = []
            for field in fields:
                if field in case.conditions:
                    cells.append(self.terms_of(field, tuple(case.conditions[field])))
                elif field in (case.every or {}):
                    every = self.terms_of(field, tuple((case.every or {})[field]))
                    cells.append(f"every value is {every}")
                else:
                    cells.append(ANY)
            rows.append([*cells, self.penalty(case.penalty)])
        blank = [MISSING] * (len(fields) - 1)
        empty = "No row holds, and a field is empty"
        unmatched = "No row holds, and no field is empty"
        rows.append([empty, *blank, self.outcome(table, table.empty_marked)])
        rows.append([unmatched, *blank, self.outcome(table, table.unmatched_marked)])
        headers = [self.title(field) for field in fields]
        return TableText([*headers, "Penalty"], rows, [])

    def render(self, criterion: Criterion[Table]) -> TableText:
        """Write the table of a criterion by the kind of table it declares.

        Args:
            criterion: The criterion.

        Returns:
            The table.

        Raises:
            TypeError: The criterion declares a kind of table this class cannot write.
        """
        match criterion.table:
            case Bands() as bands:
                return self.bands(criterion.title, bands)
            case Classes() as classes:
                return self.classes(classes)
            case Cases() as cases:
                return self.cases(cases)
        raise TypeError(f"{criterion.identifier}: no table to write")


class SchemeReference:
    """Markdown for the quality scheme pages, rendered from the worked examples.

    The Markdown is written in ``templates/quality_scheme.md.jinja``. This class gives
    the template the schema and the examples, and writes each example's values.

    Args:
        schema: The field schema the examples' field codes belong to.
        examples: The parsed worked examples file. Without it, the packaged file.
        vocabularies: Where the allowed values come from, for the terms of the criteria
            tables. Without it, the cache directory.
        criteria: The declared criteria by identifier. Without it, those of the scheme.
    """

    def __init__(
        self,
        schema: Schema,
        examples: Mapping[str, Any] | None = None,
        vocabularies: Vocabularies | None = None,
        criteria: Mapping[str, Criterion[Any]] | None = None,
    ) -> None:
        self.schema = schema
        self.declared = CRITERIA if criteria is None else criteria
        self.tables = CriterionTable(
            schema, Vocabularies() if vocabularies is None else vocabularies
        )
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
            decision=self.decision,
            lowest=self.lowest,
            highest=self.highest,
            criterion=self.criterion,
            fields=self.fields,
            examples=self.examples,
            field_legend=self.field_legend,
            coverage=self.coverage,
        )

    @staticmethod
    def lowest(part: str | None = None) -> str:
        """Write the lowest score of a part of the scheme, from its declarations.

        Args:
            part: ``probe-t``, ``probe-tc``, ``borehole-t`` or ``borehole-tc``. Without
                it, the lowest of them all.

        Returns:
            The score, such as ``0.2``.
        """
        ranges = RANGES.values() if part is None else [RANGES[part]]
        return f"{min(each.lowest() for each in ranges):g}"

    @staticmethod
    def highest(part: str | None = None) -> str:
        """Write the highest score of a part of the scheme, from its declarations.

        Args:
            part: ``probe-t``, ``probe-tc``, ``borehole-t`` or ``borehole-tc``. Without
                it, the highest of them all.

        Returns:
            The score, such as ``1.2``.
        """
        ranges = RANGES.values() if part is None else [RANGES[part]]
        return f"{max(each.highest() for each in ranges):g}"

    @staticmethod
    def decision(number: int) -> str:
        """Cite one of the GHFDB portal's quality-score decisions.

        Args:
            number: The decision's number in the portal's decisions file.

        Returns:
            Markdown naming the decision by its heading, linked to that heading on
            GitHub.

        Raises:
            KeyError: The page cites a decision this extension does not know.
        """
        heading = DECISIONS[number]
        full = f"D{number} — {heading}"
        anchor = re.sub(r"[^\w\s-]", "", full.lower()).replace(" ", "-")
        text = heading.replace("`", "")
        return f"GHFDB portal decision [D{number}, “{text}”]({DECISIONS_URL}#{anchor})"

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
        own = "own " if example.get("scoring") == "measurement" else ""
        parts = [
            f"{own if key in OWN_SCORES else ''}{label} {self.value(expected[key])}"
            for key, label in EXPECTED_LABELS.items()
            if key in expected
        ]
        if "marked" in expected:
            parts.append(
                "missing-information mark" if expected["marked"] else "no mark"
            )
        if "measurement" in expected:
            scores = expected["measurement"]
            parts.append(
                f"own scores T-score {self.value(scores['T'])}, "
                f"TC-score {self.value(scores['TC'])}"
            )
        return ", ".join(parts)

    @staticmethod
    def tests(example: Mapping[str, Any]) -> str:
        """Link the tests that assert an example.

        Args:
            example: One example of the file.

        Returns:
            One link per test to the test's file, each reading as the test's name. A
            test under ``tests/test_qc/`` is this package's, any other the GHFDB
            portal's.
        """
        links = []
        for test in example["portal_tests"]:
            path, _, name = test.partition("::")
            own = path.startswith(PACKAGE_TEST_DIRECTORY)
            base = PACKAGE_TESTS if own else PORTAL_TESTS
            links.append(f"[{FieldReference.code(name)}]({base}{path})")
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

    def criterion(self, identifier: str) -> str:
        """Write the penalty table of one criterion, from its declaration.

        Args:
            identifier: The criterion's identifier, such as ``probe-t.penetration``.

        Returns:
            A Markdown table with a row for each row of the declaration, then a row
            for an empty value and one for a value that fits no row.

        Raises:
            KeyError: No criterion is declared with the identifier.
        """
        return str(
            self.macros.penalty_table(self.tables.render(self.declared[identifier]))
        )

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
