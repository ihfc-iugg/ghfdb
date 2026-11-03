# Tasks: A generated upload template

**Input**: `plan.md`, `research.md`, `decisions.md` and `spec.md` in this directory.

**Tests**: every behaviour below is written test-first, per
`docs/contributing/standards/testing.md`. No test asserts wording or layout.

**Order**: US2 is built first, because the documentation (US1) publishes the workbook a developer
generates (US2, AS 2.1–2.2), with the same call. Within a story, groups run in order, and each
leaves the tree green.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: User Story 2 - A developer generates the upload template with the package (Priority: P2)

**Goal**: `UploadTemplate().write(path)` writes a template generated from the field schema, with
the layout of today's template and choice lists that offer and never reject, never replaces a
file unless asked, and always produces the same content.

**Independent Test**: generate the template to a new file and compare its columns, description
rows and choice lists with the field schema; generate it again to an existing path with and
without `replace=True`; compare two generations.

### Group 1 — the workbook

- [ ] T001 [US2] `pyproject.toml`: `openpyxl>=3.1` moves from the development group to
  `[project] dependencies`; `uv lock`. deptry stays clean.
- [ ] T002 [US2] `src/ghfdb/template.py`: `UploadTemplate` with `schema`, `version` and
  `workbook()` building the three sheets in order, `data list` row 1 (`ID` and every code in
  schema order) and the row labels in A2–A8 (plan.md, "`ghfdb.template`"). Layout test against
  `tests/sources/upload-template.xlsx` (SC-001, SC-004).
- [ ] T003 [US2] The description rows 2–8 from the field schema, with the `-` marker and the range
  formatting (plan.md, "Range formatting"; research.md, "Description rows") (FR-003, SC-002).
- [ ] T004 [US2] The `controlled vocabulary` sheet and a choice list on every field with allowed
  values, rows 9 to 1,048,576, no error message; none on any other field. `TemplateError` for a
  vocabulary field with no allowed values (FR-004, FR-005, FR-006, SC-003; decisions.md D-9).
- [ ] T005 [US2] The `readme` sheet: package version, vocabulary release and DOI, the field
  reference URL, how to fill it in (FR-007).

### Group 2 — writing to a path

- [ ] T006 [US2] `UploadTemplate.write(path, replace=False)`: writes to a new path, refuses an
  existing one with `FileExistsError` leaving it untouched, the message naming the path, replaces
  with `replace=True` (FR-010).
- [ ] T007 [US2] Two generations have identical content: sheets, cell values and validations,
  compared by the `workbook_content` fixture in `tests/conftest.py` (FR-011).
- [ ] T008 [US2] `docs/reference/python-api.md`: an "Upload template" section with
  `automodule:: ghfdb.template`. `docs/developer/upload-template.md`, added to the "Developer
  guide" toctree in `docs/index.md`: generate, choose a path, replace, read the version and
  release. CHANGELOG `Added` line for
  `ghfdb.template` and `Changed` line for openpyxl becoming a runtime dependency (FR-012).

---

## Phase 2: User Story 1 - A data assessor downloads the upload template and fills it in (Priority: P1)

**Goal**: the documentation site links the template generated for its version, with a list of
what changed from the hand-maintained template.

**Independent Test**: build the documentation, follow the home page to the template page and
download the file, and compare it with one written by `UploadTemplate().write()`.

### Group 1 — publishing it

- [ ] T009 [US1] `docs/extensions/upload_template.py`: `template_name`, `write_template`, the
  download marker in `source-read`, `setup`; registered in `docs/conf.py`; `.gitignore` entry
  (FR-008, SC-006).
- [ ] T010 [US1] `TemplateChanges` and the changes marker (plan.md,
  "`docs/extensions/upload_template.py`") (FR-009).
- [ ] T011 [US1] `docs/upload-template/index.md` with the Mermaid flowchart, the download and the
  changes marker, linked first from the home page under "Contributing data" (SC-005). A Guides
  table in the Project additions of `docs/contributing/standards/documentation.md`. README line,
  CHANGELOG `Added` line for the download. `sphinx-build -W` passes and the built page
  links the file.

---

## Fixes made at convergence

- [x] T012 [US1] Move the Guides table under the Project additions' existing rules in
  `docs/contributing/standards/documentation.md`, and link the developer guide from the
  contributor guide's index, as its section 4 asks.

## Fixes from the code review

- [x] T013 [US2] The developer guide's example for a different field schema writes to a path of
  its own, so it no longer fails on the file the first example wrote.
- [x] T014 [US2] Test the range row of a whole-number field, and that the readme links the field
  reference.
- [x] T015 [US1] The template page says how the `controlled vocabulary` sheet's layout changed, and
  the empty-section test reads the structure, not the wording.
