# Tasks: Preview quality scores for each child

**Input**: `plan.md`, `research.md`, `decisions.md` and `spec.md` in this directory.

**Tests**: every behaviour below is written test-first, per
`docs/contributing/standards/testing.md`. No test asserts wording or layout. The worked examples
are run by parametrised tests keyed by their identifiers, loaded from
`ghfdb/qc/worked_examples.json` through `importlib.resources`, and a test asserts that every
example outside `inheritance` is run by exactly one of them, so an example cannot be skipped
silently.

**Order**: US-2 first, in four groups, because the report reads its scores. US-1 follows in one
group. Each group leaves the tree green and documents the public names it introduces.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: User Story 2 - A developer scores a dataset from Python (Priority: P2)

**Goal**: `Dataset.scores()` gives every child its U-score, T-score, TC-score, M-score with its
mark, perturbation flags, quality code and own scores, and all 184 worked examples outside the
inherited code pass.

**Independent Test**: run every worked example through `Dataset.scores()`, or through the M-score
function for the `m-score` part, and compare with its expected scores.

### Group 1 — inputs, routing, the U-score and the flags

- [ ] T001 [US2] `ghfdb/qc/scheme.py`: the concept URIs of every term the scheme pages name, by
  field code, and `Terms`, which resolves them to the terms the fields accept through
  `ghfdb.fields.allowed_values` and raises `MissingSchemeError` naming the concept when one is not
  an allowed value (FR-010). `Inputs`: the scored fields of a dataset parsed once, numbers as
  floats, terms as concept URIs, and any value that does not parse or is not an allowed term read
  as empty (AS 2.4). Numbers parse as the check parses a number field. A cell holding a Python list
  holds several values, in any scored field, held as one row per value; text is never split
  (D-6). `DatasetCheck.blank` is called as it is. Tests: resolution against the test vocabularies, a withdrawn concept fails naming it, and one test resolves against
  the vocabularies as currently published (`published_vocabularies`).
- [ ] T002 [US2] `Scores` in `ghfdb/qc/scores.py`, routing first, reusing the domain concepts of
  `ghfdb/qc/rules.py`: probe sensing, borehole and mine, or none. Worked examples: `routing`.
- [ ] T003 [US2] `UScore` in `ghfdb/qc/uncertainty.py`: the U-score, rounding, sign and the not-determined
  inputs. Worked examples: `u-score`.
- [ ] T004 [US2] The perturbation flags in `ghfdb/qc/scores.py`. Worked examples:
  `perturbation-flags`.
- [ ] T005 [US2] The tests mirror the modules: `tests/test_qc/test_scheme.py`,
  `test_uncertainty.py`, `test_probe.py`, `test_borehole.py` and `test_scores.py`. Each
  parametrises over the examples of its parts, selected by `part`. `test_scores.py` gains the
  coverage test: the identifiers the parametrised tests ran, collected from the test modules'
  parameter lists, equal the identifiers in the file outside `inheritance`, counted from the file
  independently of the selection. Parts not built yet are listed in the test as pending, and the
  list is emptied by the group that builds them.
- [x] T016 [US2] `docs/contributing/python-api.md`: a section on the scoring classes, so the
  public names of this group are documented in the group that adds them.

### Group 2 — the probe-sensing rules

- [ ] T006 [US2] `ProbeRules` in `ghfdb/qc/probe.py`: the T-score criteria (penetration, recordings, water depth,
  tilt) and both waivers for a child, and the own T-score without them. Worked examples: `probe-t`.
- [ ] T007 [US2] The TC-score criteria (location, saturation cases, number with the literature
  exception, pT cases). Worked examples: `probe-tc`.
- [x] T017 [US2] Move `Penalty` and `Score` from `ghfdb/qc/probe.py` to `ghfdb/qc/scheme.py`, where
  the borehole rules can use them, and document them on the Python API page.

### Group 3 — the borehole and mine rules

- [ ] T008 [US2] `BoreholeRules` in `ghfdb/qc/borehole.py`: the T-score's three cases and their groups, the
  unmatched method, the empty methods. Worked examples: `borehole-t`.
- [ ] T009 [US2] The TC-score's depth gate, location, source, number with the literature
  exception, saturation, and the pT agreement with `C11` for a child and the pT conditions alone
  for the own TC-score. Worked examples: `borehole-tc`.

### Group 4 — the M-score, the code and the dataset

- [ ] T010 [US2] The M-score in `ghfdb/qc/scores.py`: the product, its rounding, the classes with
  a boundary taking the better class, the mark, and `Mx`. Worked examples: `m-score`.
- [ ] T011 [US2] `score(inputs, terms)` assembling the table of plan.md "Shapes", and the quality
  code. `Dataset.scores(problems=None, vocabularies=None)` in `ghfdb/dataset.py`, blanking the
  cells `problems` names in `code` with the kinds of D-3. Worked examples: `child`, own scores
  included. Tests: a child whose scores cannot be made shows `<NA>`, `Ux` and `Mx` and never 0
  (FR-004), a cell named by a wrong-type problem is scored as empty and marks the M-score, a rule
  problem blanks the field in its `code` and not the one in `related`, and an out-of-range tilt
  scores differently with and without its problem (D-4).
- [ ] T012 [US2] `docs/contributing/python-api.md`: `Dataset.scores` and the columns it returns.
  `docs/reference/quality-scheme/index.md` and `worked-examples.md`, and `CONTEXT.md`'s
  **Quality scheme**, **Worked example** and **Preview score**: the package computes the scores
  and runs the examples (FR-012). The coverage test's pending list is empty.

---

## Phase 2: User Story 1 - A data assessor previews the quality score of every child (Priority: P1)

**Goal**: `ghfdb check` writes a report that also gives every child its preview scores, and the
90,000-child workbook is still checked, scored and reported in under 15 seconds.

**Independent Test**: check a workbook whose children are the `child` worked examples and compare
each child's scores in the report with its expected scores.

### Group 1 — the command, the report and the speed

- [ ] T013 [US1] `ghfdb check` scores the dataset with the problems it found, and `Report` takes
  the scores: the **Preview scores** table and the summary's link to the scheme (plan.md,
  "Report"). Tests read the report's table back by its column headings: every child of a workbook
  built from the `child` examples has its expected scores against its Excel row (SC-002), a child
  with problems is scored and says so (AS 1.5), a workbook with no problems is still scored (AS
  1.6), a workbook with no children has an empty scores table, the scores in the report equal
  `Dataset.scores(problems=…)` given the same problems, for every child (SC-003), and every score
  heading and the summary link to a page of the scheme reference that the documentation build
  produces (FR-006, SC-005).
- [ ] T014 [US1] `tests/test_cli.py::TestSpeed` asserts that the report has a score for every
  child of the 90,000, inside the same 15 s limit (SC-004, FR-011).
- [ ] T015 [US1] `docs/user-guide/check.md`: the scores in the report, and where each part is
  explained. `CONTEXT.md`'s **Report**. `README.md`: the package scores a workbook. `CHANGELOG.md` under **Added**. `docs/ROADMAP.md`: R6
  loses its deliverable about disagreements with another implementation.

---

## Phase 3: Review fixes

- [ ] T018 [US2] REV-001: `poorest`, `cases` and `bands` become classmethods of `Penalty`,
  `total` a classmethod of `Score`, and `combinations` a staticmethod of `Inputs`, in
  `ghfdb/qc/scheme.py`, with the call sites and the Python API page updated. No behaviour changes.
- [ ] T019 [US1] REV-002: the report and command tests assert "Has problems" against the report
  module's own yes and no values, so an inverted value fails.
- [ ] T020 [US1] REV-003: a report with no children says there is no child to score, as the spec's
  edge case asks, with its test and the user guide line.
- [ ] T021 [US2] REV-004: the scheme overview's "Several values in one field" states how the code
  reads several values: number fields value by value and how `C1` and `C2` pair, routing, the
  flags and the two probe waivers reading the first value, and a borehole gradient's case chosen
  once for the child. Recorded under **Scheme changes** in the changelog.
- [ ] T022 [US1] REV-005: the Python API page describes `Report` with its scores argument.
- [ ] T023 [US2] REV-007: `Scores.blank` cites ADR 0007.
- [ ] T024 [US2] REV-008: `Dataset.scores` takes an optional `schema`, as `Dataset.check` does, and
  the command passes the schema it already loaded.
- [ ] T025 [US1] REV-009: roadmap R6 says the report names the package version until R8, and
  no longer says the scores go into a copy of the workbook.
