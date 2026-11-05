# Implementation Plan: Check a workbook and get a report of every problem

**Branch**: `003-check-a-workbook` | **Spec**: [spec.md](spec.md) | **Research**: [research.md](research.md) | **Decisions**: [decisions.md](decisions.md)

## Summary

`ghfdb check <workbook>` reads the `data list` sheet once, as text, with fastexcel, checks every field with polars expressions built from the field schema, adds
suggestions to not-in-vocabulary problems with `difflib`, and writes a report of the problems and a
summary with XlsxWriter beside the workbook. The tools are chosen for the finished package: a
workbook of 90,000 children is checked and reported in about 8.5 seconds on the development
machine, against the 15 seconds SC-006 allows. Nothing ever writes to the workbook's path.

## Technical Context

- **Language**: Python 3.12+, managed with uv, built with hatchling.
- **New runtime dependencies**: `polars`, `fastexcel`, `xlsxwriter` (research.md, "Dependencies
  added"). Floors set to the versions measured: `polars>=1.30`, `fastexcel>=0.21`,
  `xlsxwriter>=3.2`.
- **Existing dependencies used**: `frictionless` (the field schema, as `load_schema` returns it),
  `rdflib` (the release of each scheme).
- **Standard library**: `argparse`, `difflib`, `dataclasses`, `enum`, `os`, `re`, `tempfile`,
  `zipfile`.
- **Existing dependency no longer needed by the check**: openpyxl stays for the template only.
- **Reads**: `ghfdb.fields.load_schema(vocabularies=…)`, a `frictionless.Schema` with an `enum` on
  every vocabulary field. `ghfdb.template.ROW_LABELS` for the description rows.
- **Tests**: pytest. Test workbooks are generated with `UploadTemplate` or written with XlsxWriter in
  `tmp_path`, checked, and the report read back with fastexcel or openpyxl. Vocabularies come from
  the existing session `schema` fixture.
- **Checks**: mypy strict (polars and fastexcel ship type hints; XlsxWriter has `types-xlsxwriter`
  in the development group if mypy needs it), deptry, pre-commit (ruff, line length 88), coverage
  floors 90 % project and 85 % patch, documentation built with `-W`.

## Constitution Check

| Article | How the plan meets it |
|---|---|
| II Simplicity | fastexcel reads, polars checks, XlsxWriter writes, `difflib` suggests, `argparse` parses. Our code is the layout of the template, seven rule expressions and the report's layout. |
| III Anti-abstraction | No base class, no rule registry. One dataclass for the column problems and one `StrEnum` of kinds. Problems on children are rows of a polars table, not objects. |
| IV Integration-first | Every behaviour is tested as an assessor meets it: a workbook in, `check`, a report out. |
| V Data safety | fastexcel reads saved values and never evaluate a formula. Every value from the workbook reaches the report through `write_string`, so none becomes a formula. The report path comes from the path the assessor gave, never from the workbook's contents. |
| VI Documentation | A reference page for the command and the report, the Python API entry, README, CONTEXT.md and CHANGELOG, in this pull request. |
| VII Dependencies | Three added, each replacing custom code or a measured failure of SC-006 (research.md). deptry stays clean. |
| VIII Cohesion | `UploadWorkbook` holds the reading, `WorkbookCheck` the checking, `Report` the writing. |
| IX Sources | Every rule is the field schema's, which already sources each fact. A problem names the field whose rule it broke. |
| XI Vocabulary | Allowed terms and suggestions come from the field's `enum`, filled from the published vocabularies. |
| XII Report, never modify | No code path writes to the workbook's path, and a test compares its bytes before and after every kind of run. Text in a number field is wrong type, a fraction in a whole-number field is wrong type, row numbers are Excel's, including for a sheet that does not start at A1. |
| XIII Whole columns | Every check is a polars expression on a whole column. The only Python loops are over the 70 fields, a field's distinct not-in-vocabulary values and the error cells found. |
| XIV Compatibility | The command, the report layout and the `ghfdb.qc` API are new public interface, recorded in `CHANGELOG.md`. |
| XV Stack | **Amended in this pull request** to name polars for tabular data in place of pandas (T001). polars is measured inside SC-006 here, pandas is not: the per-cell type rules need nullable text columns and vectorised casts that polars gives directly. The constitution's version is bumped. |
| X Rules change together | Not engaged: no validation rule or scheme rule is changed. The checks apply the field schema's existing rules. |
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
ghfdb/qc/__init__.py              # exports UploadWorkbook, WorkbookCheck, Report, Kind, ColumnProblem, CheckError
ghfdb/qc/workbook.py              # CheckError, UploadWorkbook: header, columns, children, Excel rows
ghfdb/qc/check.py                 # Kind, ColumnProblem, WorkbookCheck: the rule expressions, suggestions
ghfdb/qc/report.py                # Report: the report file
ghfdb/cli.py                      # main(), run(): `ghfdb check <workbook>`
ghfdb/fields/vocabularies.py      # Vocabularies.releases()
pyproject.toml                    # dependencies; [project.scripts] ghfdb = "ghfdb.cli:run"; slow marker
tests/test_qc/__init__.py
tests/test_qc/test_workbook.py
tests/test_qc/test_check.py
tests/test_qc/test_report.py
tests/test_cli.py                 # includes TestSpeed (SC-006)
tests/test_fields/test_vocabularies.py   # TestReleases
tests/conftest.py                 # filled_workbook and large_workbook fixtures
docs/reference/check.md           # the command, the report, every problem kind
docs/reference/index.md           # toctree entry
docs/reference/python-api.md      # ghfdb.qc section
README.md, CONTEXT.md, CHANGELOG.md
```

## Design

### `ghfdb.qc.workbook`

- `CheckError(Exception)`: every could-not-run case, with a message naming what is wrong: a file
  that cannot be opened (including `.xls`), no `data list` sheet, no header row found, a report
  that cannot be written.
- `UploadWorkbook(path, schema)`, read once with fastexcel:
  - `fastexcel.read_excel(path).load_sheet_by_name("data list", header_row=None, skip_rows=0,
    dtypes="string")`. With `skip_rows=0` the first row of the frame is Excel row 1, and each
    column's sheet position is `ColumnInfo.absolute_index` (research.md), so a child's Excel row
    is its position plus 1 and every column is matched to its sheet column directly, whichever
    cell the sheet starts at. Any `fastexcel.FastExcelError` while opening or reading becomes
    `CheckError` naming the file (`SheetNotFoundError` as no `data list` sheet).
  - `header_row`: the first of the first 20 rows in which more than half of the non-empty cells
    after the first filled column name a field, by code, published column name or earlier column
    name. The first filled column (`ID`) is matched to no field and is never an unknown column.
  - `columns`: each field and the first column naming it. Also `unknown_columns`,
    `absent_fields` and `duplicate_columns`, for the column problems.
  - `first_data_row`: the first row under the header whose first filled cell is not a
    description label (`ROW_LABELS`, case-folded and stripped).
  - **Error cells.** fastexcel reads a cell holding an Excel error (`#N/A`, `#DIV/0!`) as empty.
    The check finds those cells by scanning the `data list` sheet's XML in the file for cells of
    type `e` (a byte search on the stream, `zipfile` and `re`, no XML parser; 0.65 s on the
    90,000-child workbook) and puts their error text in place of the empty value, so an error is
    checked like any other text and is never reported as missing (FR-004, Article XII).
  - `frame`: one row per child, one text column per field found, named by code, plus `row`.
    Spaces-only cells become null. Rows with every field null are dropped: they are not children.

### `ghfdb.qc.check`

- `Kind(StrEnum)`: `missing`, `wrong type`, `out of range`, `not in vocabulary`, `unknown column`,
  `no column`, `duplicate column`.
- `ColumnProblem`: frozen dataclass `kind`, `code` (or `None`), `column` (the header text).
- `WorkbookCheck(workbook, schema)`:
  - `column_problems()`: one `ColumnProblem` per unknown column, absent field and duplicate.
  - `problems()`: a polars frame with columns `row`, `code`, `column_name`, `kind`, `value`,
    `suggestion`, ordered by row and then field order. For each field present, the expressions in
    research.md's table, evaluated on its column:
    - empty, and the obligation is `M` with domain `B` and `S` → missing. An absent mandatory field
      gives a missing problem on every child (AS 1.16), from a column of nulls.
    - for `number` and `integer`: the stripped text cast to `Float64` with `strict=False`; null,
      NaN or infinite where the text is not empty → wrong type; for `integer`, not equal to its
      floor → wrong type. Range is checked only on the values that passed.
    - `pattern`, anchored as `^(?:…)$` → wrong type; `maxLength` → out of range; `minimum` and
      `maximum` → out of range; `enum` → not in vocabulary. A field with a `separator` and an
      `enum` or `pattern` is split and exploded first, so each value is checked on its own and
      keeps its Excel row (AS 1.10).
  - `suggestions(code, values)`: for the distinct not-in-vocabulary values of a field, the one
    closest term (research.md, "Suggestions"), joined back onto the problems.

### `ghfdb.qc.report.Report`

`Report(workbook_path, column_problems, problems, children, vocabularies)` and `write() -> Path`.

- Path: `<stem>.report.xlsx` in the workbook's folder. It is written to a temporary file in the
  same folder (`tempfile.NamedTemporaryFile(delete=False, dir=…, suffix=".xlsx")`) and moved over
  the earlier report with `os.replace`, so a failure leaves the earlier one whole. Any `OSError`
  becomes `CheckError` naming the report. When the report path exists and `os.path.samefile` says
  it is the workbook (a link), `write` refuses.
- A `problems` sheet: one row per problem, column problems first with no row: Excel row, field
  code, published column name, kind, value, suggestion. Written in XlsxWriter's constant-memory
  mode, every value from the workbook with `write_string`, numbers (the row) with `write_number`.
- A `summary` sheet: the workbook's file name, package version, time of the check, the vocabulary
  release or releases (`Vocabularies.releases()`), the number of children, problems and children
  with problems, and a line saying no problem was found when there is none.
- The layout (column order, widths, headings, a frozen header row, an autofilter) is not tested.

### `Vocabularies.releases()`

In `ghfdb/fields/vocabularies.py`: the sorted `dcterms:isPartOf` URIs of every scheme graph the
instance has read. `load_schema` reads through the instance it is given, so the command passes its
own and asks it afterwards.

### `ghfdb.cli`

`main(argv: list[str] | None = None) -> int`, with `argparse` and one subcommand, `check`, taking
the workbook's path. It loads the schema, builds `UploadWorkbook`, `WorkbookCheck` and `Report`,
writes the report, prints one line ("212 children, 37 problems in 14 of them, report:
<path>") and returns `0` or `1`. `CheckError`, `OSError` and `MissingSchemeError` print their
message to standard error and return `2`; an `OSError` while loading the vocabularies says they
must be downloaded once with a network connection. `run()` is `sys.exit(main())`, and
`[project.scripts] ghfdb = "ghfdb.cli:run"`.

## Testing approach

- `filled_workbook` fixture in `tests/conftest.py`: generates the template with
  `UploadTemplate(schema)`, writes children given as `{code: value}` dicts from row 9 with
  openpyxl, and returns the path. The valid child is built from the schema: a value inside each
  field's range, the first term of its `enum`, `2020-05` for the year-and-month pattern, or text,
  so the tests type no term in by hand (Article XI). A test that needs another layout (more
  description rows, a sheet starting at B3, an earlier column name, an unknown column) edits that
  workbook before checking it.
- Problems are asserted as sets of `(row, code, kind)`, never their wording.
- The byte-for-byte test hashes the original before and after a run with problems, a run with none
  and a run whose report cannot be written.
- **Vocabularies in tests.** A fixture in `tests/conftest.py` monkeypatches
  `ghfdb.fields.vocabularies.user_cache_dir`, as `tests/test_fields/test_vocabularies.py` already
  does, so `main` reads the directory the session `published_vocabularies` fixture has filled. No
  test writes outside its own directories, and `TestSpeed` times a warm load (0.2 s), never a
  download (9 s). The offline test points it at its own `tmp_path`.
- The CLI is tested through `main([...])`: the returned status, standard error for could-not-run,
  and the report read back.
- Offline: vocabularies cached through `caching_session(tmp_path)`, then the check run with
  `responses` refusing every request, with the same problems.
- **Speed (SC-006, D-8):** `large_workbook`, a session fixture, writes 90,000 children with every
  field filled and a seeded problem in one in a hundred, with XlsxWriter in constant-memory mode.
  `TestSpeed` times
  `main(["check", path])` and fails above 15 seconds, and checks that the number of problems is
  the number seeded. Marked `slow` (registered in `pyproject.toml`), and run by default.

## Complexity Tracking

| Item | Why it is needed |
|---|---|
| Three new dependencies | Measured: openpyxl reading, Frictionless validating and any full rewrite of the workbook each miss SC-006 alone (research.md). |
| An error-cell scan | fastexcel and calamine read Excel error values as empty, which would report `#N/A` in a mandatory field as missing. |
| Seven rule expressions of ours | pandera, the column-wise package found, accepts `3.5` in a whole-number field; Frictionless is right but too slow. |
| A 90,000-child test | SC-006 is measured on every change (FR-016), so a slower change fails its pull request. |
