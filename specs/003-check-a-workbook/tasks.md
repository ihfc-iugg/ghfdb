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

**Goal**: `ghfdb check <workbook>` writes a report copy beside the workbook listing every problem
by Excel row, field and kind, with suggestions, and never changes the workbook.

**Independent Test**: check a workbook seeded with one problem of each kind, compare the report
copy with the seeded list, and compare the original's bytes with a copy taken before.

### Group 1 — reading the workbook

- [ ] T001 [US1] `tests/conftest.py`: the `filled_workbook` fixture (plan.md, "Testing
  approach"), building valid children from the schema's ranges and `enum`s.
- [ ] T002 [US1] `ghfdb/qc/workbook.py`: `CheckError` and `UploadWorkbook` with `header_row`,
  `columns`, `first_data_row`, `children`. The header is found by field code, published column
  name or earlier column name. Description rows are skipped by label, whatever their number
  (D-4). Rows holding nothing outside `ID` are not children. `CheckError` for a file that cannot
  be opened, no `data list` sheet, no header (AS 1.13, 1.14, 1.15, FR-008, FR-009). Tested on a
  generated template and on `tests/sources/upload-template.xlsx` filled with the same children.
- [ ] T003 [US1] `UploadWorkbook.values(field)`, `unknown_columns`, `absent_fields`,
  `duplicate_columns`: the column's values for the children, spaces-only made `None`, the
  first column used when two name one field, a column of `None` for an absent field. A formula
  cell reads as its saved value, and as `None` with none saved (Edge Cases).
- [ ] T004 [US1] `ghfdb/qc/__init__.py` exports; `docs/reference/python-api.md` gains a
  "Checking a workbook" section with `automodule:: ghfdb.qc.workbook`.

### Group 2 — the check

- [ ] T005 [US1] `ghfdb/qc/check.py`: `Problem` and its `Kind`, and `WorkbookCheck.problems()`
  for missing (fields mandatory in both domains only), wrong type, out of range and not in
  vocabulary, by the error-to-kind table in research.md, each with its Excel row, code, published
  column name and value as found (AS 1.2–1.8, 1.11, 1.12, FR-003–FR-006). A number stored as text
  is accepted, `1,234.5` and `12,5` are wrong type, a date in a year-and-month field is wrong type
  (D-1, D-2). The schema passed in is not changed.
- [ ] T006 [US1] Text `nan`, `inf` and `-inf` in a number field are wrong type (research.md,
  "Running the checks").
- [ ] T007 [US1] Column problems: an unknown column, a field with no column, two columns for one
  field, each reported once with no row; a mandatory field with no column is also missing on every
  child (AS 1.16).
- [ ] T008 [US1] `WorkbookCheck.suggest`: a suggestion on a not-in-vocabulary problem for a value
  missing its brackets, in another case, or slightly misspelt; none for a value close to no term
  (AS 1.9, FR-007).
- [ ] T009 [US1] A field with a separator and a vocabulary or pattern has each value checked on
  its own, with a problem per bad value naming that value. Tested with a test schema, since no
  such field exists in the packaged one (AS 1.10).
- [ ] T010 [US1] `ghfdb/fields/vocabularies.py`: `Vocabularies.releases()`, the `dcterms:isPartOf`
  of every scheme read, tested in `tests/test_fields/test_vocabularies.py` with the existing test
  vocabularies. `automodule:: ghfdb.qc.check` in the API reference. `CONTEXT.md`: **report copy**
  and **column problem** added, the column problem kinds listed with the problem kinds, "planned"
  removed from the check and upload template entries where the code now exists.

### Group 3 — the report copy and the command

- [ ] T011 [US1] `ghfdb/qc/report.py`: `Report.write()` saves `<stem>.report.xlsx` beside the
  workbook with every problem shown against its child in `data list`, a `problems` sheet listing
  every problem, and a `check` sheet with the package version, time, vocabulary releases and
  counts; it says no problem was found when there is none, and replaces an earlier report copy
  (AS 1.1, 1.17, 1.19, 1.20, FR-002, FR-010, FR-011). It refuses to write to the workbook's own
  path, and a report copy it cannot replace is a `CheckError` that leaves the earlier one as it
  was.
- [ ] T012 [US1] `ghfdb/cli.py`: `main(argv)` and `run()`, `ghfdb check <workbook>`, the summary
  line, statuses `0`/`1`/`2`, could-not-run messages on standard error for each Edge Case
  (AS 1.18, FR-001, FR-012). `pyproject.toml`: `[project.scripts] ghfdb = "ghfdb.cli:run"`.
- [ ] T013 [US1] The original workbook's bytes are unchanged after a run with problems, a run
  with none, and a run that cannot write its report (AS 1.1, 1.20, SC-003).
- [ ] T014 [US1] With the vocabularies cached by an earlier run and every request refused, the
  check gives the same problems; with nothing cached and no network, status `2` and the message
  (AS 1.21, FR-014).
- [ ] T015 [US1] The seeded workbook end to end through `main`: every seeded problem, and no
  other, in the `problems` sheet; the same data in the hand-maintained template with no problem
  (SC-001, SC-002, SC-004).
- [ ] T016 [US1] `docs/reference/check.md`: how to run the command, what it writes, every part of
  the report copy, every problem kind with an example, the statuses, and a Mermaid flowchart of
  the check; in the reference toctree; `automodule:: ghfdb.qc.report` and `ghfdb.cli` in the API
  reference (AS 1.22, FR-015). README: "The package … does not yet check or score anything"
  becomes a short "Checking a workbook" section. `CHANGELOG.md` under Added.
