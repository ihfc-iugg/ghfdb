# Implementation Plan: Preview quality scores for each child

**Branch**: `005-preview-quality-scores` | **Spec**: [spec.md](spec.md) | **Research**: [research.md](research.md)

## Summary

A new module scores every child of a dataset under the quality scheme, on whole columns, and
`Dataset.scores()` returns the result as one row per child. The check command passes the problems
it found, so their cells are scored as empty, and the report gains a second table of preview
scores. The worked examples become the test of the scoring.

## Technical context

- Python 3.12 and 3.13, pandas, frictionless, Jinja2 for the report. No new dependency.
- Tests: pytest, mirroring the source tree (`docs/contributing/standards/testing.md`). The
  vocabularies come from the cached release the existing tests use (`vocabularies_cached`).
- Performance: SC-004, the 90,000-child workbook checked, scored and reported in under 15 s,
  measured by `tests/test_cli.py::TestSpeed`.

## Constitution check

- **Simplicity.** One module per part of the scheme the pages separate, no class hierarchy for
  criteria: each criterion is a function from the inputs to a penalty and a mark.
- **Every rule traceable.** Each criterion's docstring names its page and section of the scheme,
  so the code can be read against the documentation.
- **Report-only.** The workbook is never changed. The report holds the scores and no copy of the
  data.

## Design

### Modules

| Module | Holds |
|---|---|
| `ghfdb/qc/scheme.py` | Every concept URI the scheme names, by the field it belongs to, and `Terms`: the concepts resolved to the terms of the published vocabularies, failing with `MissingSchemeError` naming the concept. `Inputs`: a dataset's scored fields as numbers, terms and the several values of a cell, with an unknown value read as empty |
| `ghfdb/qc/uncertainty.py` | `UScore`: the U-score |
| `ghfdb/qc/probe.py` | `ProbeRules`: the probe-sensing T-score and TC-score, own and child, one method per criterion |
| `ghfdb/qc/borehole.py` | `BoreholeRules`: the borehole and mine T-score and TC-score, own and child, one method per criterion |
| `ghfdb/qc/scores.py` | `Scores`: routing, the M-score, the perturbation flags, the quality code, and the table of scores assembled from the other three |

Each part is one class whose methods share the `Inputs` and `Terms` it is built with
(constitution Article VIII). There is no base class: the four classes have nothing to share
beyond those two objects.

### Shapes

- A criterion is a method that reads the `Inputs` and returns a `Penalty`: two aligned Series over the children,
  the penalty and whether it sets the mark. A T-score or TC-score is 1.0 plus the sum of its
  criteria's penalties, rounded to three places, marked when any criterion is.
- A field with several values is held exploded, one row per value with the child's index. A
  criterion that reads it scores each value and keeps the poorest per child. A workbook holds one
  value in each scored field, so several values reach the scoring only from a dataset built in
  code, as a Python list in the cell (D-6). Four worked examples give one: PC-12, BT-14, BC-38 and
  B5-drilling-clustering.
- Numbers are parsed the way the check parses a number field, so a cell the check accepts is a
  number to the scoring and a cell it rejects is empty.
- `Dataset.scores(problems=None, vocabularies=None)` returns one row per child, indexed like
  `data`, with the columns `rules`, `U`, `T`, `TC`, `marked`, `M`, `flags`, `code`, `own_T`,
  `own_TC`, `own_T_marked` and `own_TC_marked`. A score not determined is `<NA>`, or `Ux` and `Mx`.
- `problems`, when given, is the problem table of a check. Every cell it names with the kind
  missing, wrong type, out of range, not in vocabulary or rule is blanked before scoring (D-1,
  D-3). A rule problem blanks the field it names in `code`, never the field in `related`.

### Report

- A second table, **Preview scores**, after the problems: Excel row, rules, U-score, T-score,
  TC-score, M-score, perturbation flags, quality code, and whether the child has problems. Each
  heading of a score links to its page of the scheme reference, the way a rule links to its entry.
- The summary gains "Quality scheme", linking the scheme's overview. The package version it
  already states is the version that made the scores (FR-006).
- The cells of the scores table are plain strings in tuples, prepared in one pass over the scores
  frame with `itertuples`, and the template writes each row with one `join`. The links sit in the
  headings, so no cell needs a dictionary. Timed in review: about 1.4 s for 90,000 rows against
  3.9 s for a dictionary per cell rendered through Jinja, with the check alone at 7.9 s of the
  15 s (SC-004).

### Documentation

- `docs/user-guide/check.md`: the scores in the report.
- `docs/contributing/python-api.md`: `Dataset.scores`.
- `docs/reference/quality-scheme/index.md` and `worked-examples.md`: no longer say that no code
  computes the scores or runs the examples.
- `CONTEXT.md`: **Report**, **Quality scheme**, **Worked example** and **Preview score**.
- `CHANGELOG.md`: an **Added** entry.
- `README.md`: no longer says the package does not yet score a workbook.
- `docs/ROADMAP.md`: R6 loses its deliverable about disagreements with another implementation.

## Order

US-2 is built first, because the report reads its scores. US-1 follows on the same branch.

## Risks

- **Time.** The report's second table has 90,000 rows, and CI runs the suite under coverage. If
  SC-004 fails with the plain-string rows, the remedy is to profile the scoring before touching the
  report. Leaving children out of the table would change US-1 and needs a re-gate.
- **A page and an example that disagree.** The examples were written from the pages, but if the
  code meets an example it cannot satisfy without contradicting a page, it stops there and the
  disagreement is recorded, not coded around (FR-013).
