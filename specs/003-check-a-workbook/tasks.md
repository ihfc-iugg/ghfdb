# Tasks: Check a workbook and get a report of every problem

**Input**: `plan.md`, `research.md`, `decisions.md` and `spec.md` in this directory.

**Tests**: every behaviour below is written test-first, per
`docs/contributing/standards/testing.md`. No test asserts wording or layout. Problems are asserted
as `(row, code, kind)`.

**Order**: one story, built in three groups. Each group leaves the tree green, and documents the
public names it introduces.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: User Story 1 - A data assessor checks a workbook and reads every problem in it (Priority: P1)

**Goal**: `ghfdb check <workbook>` writes a report beside the workbook listing every problem by
Excel row, field and kind, with suggestions, never changes the workbook, and checks a workbook of
90,000 children in under 15 seconds.

**Independent Test**: check a workbook seeded with one problem of each kind and compare the report
with the seeded list; compare the original's bytes with a copy taken before; time the check of
90,000 children.

### Group 1 — reading the workbook

- [ ] T001 [US1] `pyproject.toml`: `polars>=1.30`, `fastexcel>=0.21` and `xlsxwriter>=3.2` in
  `[project] dependencies`; `uv lock`; deptry clean. `CONSTITUTION.md` Article XV names polars for
  tabular data in place of pandas, version bumped. `tests/conftest.py`: the `filled_workbook`
  fixture and the fixture pointing the vocabulary cache at the session's filled directory
  (plan.md, "Testing approach").
- [ ] T002 [US1] `ghfdb/qc/workbook.py`: `CheckError` and `UploadWorkbook`: `header_row`, `columns`, `first_data_row`, read once with fastexcel.
  The header is found by field code, published column name or earlier column name; the first
  column is matched to no field; description rows are skipped by label, whatever their number
  (D-4). `CheckError` for a file that cannot be opened or is not a workbook (any `FastExcelError`), no
  `data list` sheet, no header
  (AS 1.13, 1.15, FR-008, FR-009). Tested on a generated template and on
  `tests/sources/upload-template.xlsx`, neither giving a column problem.
- [ ] T003 [US1] `UploadWorkbook.frame`: field columns named by code,
  an Excel `row` column that is right for a sheet starting at A1 and for one starting at B3,
  spaces-only cells null, rows with every field empty dropped, so a row holding only an `ID` is no
  child (AS 1.12, 1.14). A formula cell reads as its saved value, and as empty with none saved
  (Edge Cases). A cell holding an Excel error value reaches the frame as its error text, so `#N/A`
  in a mandatory field is never missing. A sheet with its header at B3 and a stray cell in column A
  below keeps every field in its own column. `unknown_columns`, `absent_fields`, `duplicate_columns`, the first column used when
  two name one field.
- [ ] T004 [US1] `ghfdb/qc/__init__.py` exports; `docs/reference/python-api.md` gains a
  "Checking a workbook" section with `automodule:: ghfdb.qc.workbook`.

### Group 2 — the check

- [ ] T005 [US1] `ghfdb/qc/check.py`: `Kind`, `ColumnProblem` and `WorkbookCheck.problems()` for
  missing (fields mandatory in both domains only, D-3), wrong type (numbers, whole numbers,
  patterns), out of range (minimum, maximum, maximum length) and not in vocabulary, each with its
  Excel row, code, published column name and value as found (AS 1.2–1.8, 1.11, FR-003–FR-006). A
  number stored as text is accepted (D-1), a number in a free-text field is accepted (D-6),
  `1,234.5`, `12,5`, `true` and a date in a year-and-month field are wrong type (D-2). A cell gets
  at most one type problem, and range is checked only on values of the right type.
- [ ] T006 [US1] Text `nan`, `inf` and `-inf` in a number field, ranged or not, give exactly one
  wrong-type problem per cell (D-7).
- [ ] T007 [US1] `WorkbookCheck.column_problems()`: an unknown column, a field with no column, two
  columns for one field, each once with no row; a mandatory field with no column is also missing
  on every child (AS 1.16).
- [ ] T008 [US1] `WorkbookCheck.suggestions`: a suggestion on a not-in-vocabulary problem for a
  value missing its brackets, in another case, or slightly misspelt; none for a value close to no
  term; a value repeated on many children is matched once (AS 1.9, FR-007).
- [ ] T009 [US1] A field with a separator and a vocabulary or pattern has each value checked on its
  own, with a problem per bad value naming that value and its Excel row. Tested with a test
  schema, since no packaged field has that combination (AS 1.10).
- [ ] T010 [US1] `ghfdb/fields/vocabularies.py`: `Vocabularies.releases()`, the `dcterms:isPartOf`
  of every scheme read, tested in `tests/test_fields/test_vocabularies.py` with the existing test
  vocabularies. `automodule:: ghfdb.qc.check` in the API reference. `CONTEXT.md`: **report** and
  **column problem** added, the column problem kinds listed with the problem kinds, "planned"
  removed from the check and upload template entries where the code now exists.

### Group 3 — the report, the command and the speed

- [ ] T011 [US1] `ghfdb/qc/report.py`: `Report.write()` writes `<stem>.report.xlsx` beside the
  workbook through a temporary file and `os.replace`, with the `problems` sheet (column problems
  first) and the `summary` sheet (file name, package version, time, vocabulary releases, counts,
  and that no problem was found when there is none); it replaces an earlier report (AS 1.1, 1.17,
  1.19, 1.20, FR-002, FR-010, FR-011). A workbook value starting with `=` reaches the report as
  text, never a formula. It refuses a report path that is the workbook itself
  (`os.path.samefile`), and a report it cannot write is a `CheckError` that leaves the earlier one
  whole.
- [ ] T012 [US1] `ghfdb/cli.py`: `main(argv)` and `run()`, `ghfdb check <workbook>`, the summary
  line, statuses `0`/`1`/`2`, could-not-run messages on standard error for each Edge Case, and
  status `2` for an `OSError` or `MissingSchemeError` from the vocabularies (AS 1.18, FR-001,
  FR-012). `pyproject.toml`: `[project.scripts] ghfdb = "ghfdb.cli:run"`.
- [ ] T013 [US1] The original workbook's bytes are unchanged after a run with problems, a run with
  none, and a run whose report cannot be written (AS 1.1, 1.20, FR-013, SC-003).
- [ ] T014 [US1] With the vocabularies cached by an earlier run and every request refused, the
  check gives the same problems; with nothing cached and no network, status `2` and the message
  (AS 1.21, FR-014).
- [ ] T015 [US1] The seeded workbook end to end through `main`: every seeded problem, and no other,
  in the `problems` sheet; the same data in the hand-maintained template with no problem (SC-001,
  SC-002, SC-004).
- [ ] T016 [US1] `large_workbook` session fixture and `TestSpeed`: 90,000 children, every field
  filled, a seeded problem in one in a hundred, checked and reported through `main` in under 15
  seconds, with exactly the seeded problems; `slow` marker registered in `pyproject.toml` (AS 1.23,
  FR-016, SC-006, D-8).
- [ ] T017 [US1] `docs/reference/check.md`: the command (synopsis, argument, what it writes, the
  three statuses), each sheet and column of the report, each problem kind with a short example,
  how long a GHFDB-sized workbook takes, with a Mermaid flowchart of the check and no numbered
  steps; in the reference toctree; `automodule:: ghfdb.qc.report` and `ghfdb.cli` in the API
  reference (AS 1.22, FR-015). README: "The package … does not yet check or score anything"
  becomes a short "Checking a workbook" section. `CHANGELOG.md` under Added.
