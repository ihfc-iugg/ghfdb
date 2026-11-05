# Implementation Plan: Check a workbook and get a report of every problem

**Branch**: `003-check-a-workbook` | **Spec**: [spec.md](spec.md) | **Research**: [research.md](research.md) | **Decisions**: [decisions.md](decisions.md)

## Summary

`ghfdb check <workbook>` reads the workbook with openpyxl, finds its header and children,
validates the children's values with Frictionless against the field schema, turns each
Frictionless error into a problem with its Excel row, field and kind, adds a suggestion to
not-in-vocabulary problems with `difflib`, and saves a report copy beside the workbook. The
original is opened read-only in effect: nothing ever saves to its path. No new dependency.

## Technical Context

- **Language**: Python 3.12+, managed with uv, built with hatchling.
- **Runtime dependencies used**: `frictionless` (validation), `openpyxl` (reading and writing),
  `rdflib` (release of each scheme). All already declared. No new dependency.
- **Standard library**: `argparse`, `difflib`, `dataclasses`, `datetime`.
- **Reads**: `ghfdb.fields.load_schema(vocabularies=…)`, a `frictionless.Schema` with an `enum` on
  every vocabulary field. `ghfdb.template.ROW_LABELS` for the description rows.
- **Tests**: pytest. Every test workbook is generated with `UploadTemplate` or built with openpyxl
  in `tmp_path`, filled with a few children, checked, and the report copy read back. Vocabularies
  come from the existing session `schema` fixture.
- **Checks**: mypy strict, deptry, pre-commit (ruff, line length 88), coverage floors 90 % project
  and 85 % patch, documentation built with `-W`.

## Constitution Check

| Article | How the plan meets it |
|---|---|
| II Simplicity | Frictionless validates, openpyxl reads and writes, `difflib` suggests, `argparse` parses. Our code reads the layout, maps errors to kinds and lays out the report. |
| III Anti-abstraction | No base class. One dataclass, `Problem`, because no installed type carries an Excel row, a kind and a suggestion. |
| IV Integration-first | Every behaviour is tested as an assessor meets it: a workbook in, `check`, a report copy out. |
| V Data safety | `data_only=True`: formulas are never evaluated. Nothing read from a workbook builds a path or a command: the report path is derived from the path the assessor gave. |
| VI Documentation | A reference page for the command and the report copy, the Python API entry, README, CONTEXT.md and CHANGELOG, in this pull request. |
| VII Dependencies | None added. deptry stays clean. |
| VIII Cohesion | `UploadWorkbook` holds the reading, `WorkbookCheck` the checking, `Report` the writing. |
| IX Sources | Every rule is the field schema's, which already sources each fact. A problem names the field whose rule it broke. |
| XI Vocabulary | Allowed terms and suggestions come from the field's `enum`, filled from the published vocabularies. |
| XII Report, never modify | No code path saves to the workbook's path. A test compares the original's bytes before and after every kind of run. Text in a number field is wrong type, a fraction in a whole-number field is wrong type, row numbers are Excel's. |
| XIII Whole columns | The check's own code works on columns: finding columns, making a column empty, mapping errors. Frictionless casts row by row inside `validate`. The pull request states that, with the measurement in research.md, and leaves speed to R11. The only loop of ours over values is for a field with a separator and a vocabulary or pattern, of which the schema has none today. |
| Mermaid | The reference page shows the check as a flowchart, for readers who do not write code (G14). |

## Project Structure

### Documentation (this feature)

```text
specs/003-check-a-workbook/
├── spec.md
├── decisions.md
├── research.md
├── plan.md
└── tasks.md
```

### Source code

```text
ghfdb/qc/__init__.py              # exports UploadWorkbook, WorkbookCheck, Problem, Report, CheckError
ghfdb/qc/workbook.py              # UploadWorkbook: header, columns, children, Excel rows
ghfdb/qc/check.py                 # Problem, WorkbookCheck: validation, kinds, suggestions
ghfdb/qc/report.py                # Report: the report copy
ghfdb/cli.py                      # main(): `ghfdb check <workbook>`
ghfdb/fields/vocabularies.py      # Vocabularies.releases()
pyproject.toml                    # [project.scripts] ghfdb = "ghfdb.cli:run"
tests/test_qc/__init__.py
tests/test_qc/test_workbook.py
tests/test_qc/test_check.py
tests/test_qc/test_report.py
tests/test_cli.py
tests/test_fields/test_vocabularies.py   # TestReleases
tests/conftest.py                 # filled_workbook fixture
docs/reference/check.md           # the command, the report copy, every problem kind
docs/reference/index.md           # toctree entry
docs/reference/python-api.md      # ghfdb.qc section
README.md, CONTEXT.md, CHANGELOG.md
```

## Design

### `ghfdb.qc.workbook.UploadWorkbook`

Built from a path and a schema. Opens the file with `openpyxl.load_workbook(path, data_only=True)`
and keeps the loaded workbook, so the report is written from the same reading.

- `CheckError(Exception)`: the could-not-run cases, with a message naming what is wrong. Raised for
  a file openpyxl cannot open (including `.xls`), no `data list` sheet, no header row found.
- `header_row`: the first of rows 1–20 in which more than half of the non-empty cells name a field
  by code, published column name or earlier column name.
- `columns`: for each field, the sheet column it was found in, the first one when two name the same
  field. Also `unknown_columns`, `absent_fields` and `duplicate_columns`, for the column problems.
- `first_data_row`: the first row under the header whose column A is not a description label
  (`ROW_LABELS`, compared case-folded and stripped).
- `children`: the Excel row of every later row that holds anything outside the `ID` column.
- `values(field)`: the column's values for the children, in order, with spaces-only text made
  `None`. An absent field gives a column of `None`.

### `ghfdb.qc.check`

- `Problem`: frozen dataclass with `row: int | None` (None for a column problem), `code`,
  `column_name`, `kind`, `value`, `suggestion: str | None`. `kind` is a `StrEnum`: `missing`,
  `wrong type`, `out of range`, `not in vocabulary`, `unknown column`, `no column`,
  `duplicate column`.
- `WorkbookCheck(workbook, schema)`:
  - `schema_for_check()`: a copy of the schema (`Schema.from_descriptor(schema.to_descriptor())`,
    as `tests/conftest.py` already does) with `required` set on every field whose obligation is
    `M` and whose domain is both `B` and `S` (FR-005, D-3). For a field with a separator and a
    vocabulary or pattern, those constraints move off the column, because each value is checked
    on its own.
  - `problems()`: column problems first, then the result of
    `frictionless.validate(Resource(data=[codes, *rows], schema=…), limit_errors=None)`, each error
    mapped to a kind by the table in research.md and given the Excel row of its child, the field's
    published column name and the cell as found. Then the two extra wrong-type cases: a number
    field whose value Frictionless read as `nan` or an infinity. Then the per-value check of
    separator fields, with `Field.read_cell`. Ordered by row, then by field order.
  - `suggest(field, value)`: the one closest term of the field's `enum`, comparing values with
    brackets and surrounding spaces removed and case folded, exact match first, then
    `difflib.get_close_matches(n=1, cutoff=0.8)`; `None` otherwise.
  - The rows passed to Frictionless are built column by column from `values(field)`, then zipped.

### `ghfdb.qc.report.Report`

`Report(workbook, problems, schema, vocabularies)` and `write() -> Path`.

- Path: `<stem>.report.xlsx` in the workbook's folder. The workbook's own path is never written:
  `write` refuses, with `CheckError`, a report path equal to the workbook's.
- In `data list`: a "Problems" column after the last used column, holding for each child the list
  of its problems in one cell, and a fill on every cell that has a problem. These are layout and
  are not tested beyond the list being complete.
- A `problems` sheet: one row per problem with Excel row, field code, published column name, kind,
  value and suggestion. Column problems come first, with no row.
- A `check` sheet: package version, time of the check, the vocabulary release or releases
  (`Vocabularies.releases()`), the number of children, problems and children with problems, and a
  line saying no problem was found when there is none.
- Saved with openpyxl. A `PermissionError` becomes `CheckError` naming the report copy.

### `Vocabularies.releases()`

In `ghfdb/fields/vocabularies.py`: the sorted `dcterms:isPartOf` URIs of every scheme graph the
instance has read. `load_schema` reads through the instance it is given, so the check passes its
own and asks it afterwards.

### `ghfdb.cli.main(argv=None) -> int`

`argparse` with one subcommand, `check`, and one argument, the workbook's path. Loads the schema
(an `OSError` from the vocabularies becomes the could-not-run message saying they must be
downloaded once), runs the check, writes the report, prints one summary line ("212 children, 37
problems in 14 of them, report: <path>"), and returns `0`, `1` or `2`. Could-not-run messages go
to standard error. `run()` is `sys.exit(main())`, and `[project.scripts] ghfdb = "ghfdb.cli:run"`
points at it, so the tests call `main` and read its status.

## Testing approach

- One `filled_workbook` fixture in `tests/conftest.py`: generates the template with
  `UploadTemplate(schema)`, writes children given as `{code: value}` dicts from row 9, and returns
  the path. A test that needs another layout (more description rows, an earlier column name, an
  unknown column) edits that workbook with openpyxl before checking it.
- The valid child is built from the schema: a value inside each field's range or the first term of
  its `enum`, so the tests do not type terms in by hand (Article XI).
- Problems are asserted as `(row, code, kind)` sets, never their wording.
- The byte-for-byte test hashes the original before and after a run that finds problems, a run
  that finds none, and a run that cannot write its report.
- The CLI is tested by calling `main([...])` and reading the returned status and the report copy.
- Offline: a test caches the vocabularies through `caching_session(tmp_path)`, then runs with
  `responses` refusing every request, and gets the same problems.

## Complexity Tracking

| Item | Why it is needed |
|---|---|
| `Problem` dataclass | No installed type carries an Excel row, a kind of ours and a suggestion. |
| Frictionless's row-by-row casting (Article XIII) | Already a dependency and finds every seeded problem correctly. The column-wise alternative found (pandera) misses a fraction in a whole-number field. Speed is R11's. |
