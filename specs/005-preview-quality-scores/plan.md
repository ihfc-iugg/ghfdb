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
| `ghfdb/qc/uncertainty.py` | The U-score |
| `ghfdb/qc/probe.py` | The probe-sensing T-score and TC-score, own and child |
| `ghfdb/qc/borehole.py` | The borehole and mine T-score and TC-score, own and child |
| `ghfdb/qc/scores.py` | Routing, the M-score, the perturbation flags, the quality code, and `score(data, terms)` assembling the table of scores |

### Shapes

- A criterion takes the `Inputs` and returns a `Penalty`: two aligned Series over the children,
  the penalty and whether it sets the mark. A T-score or TC-score is 1.0 plus the sum of its
  criteria's penalties, rounded to three places, marked when any criterion is.
- A field with several values is held exploded, one row per value with the child's index. A
  criterion that reads it scores each value and keeps the poorest per child.
- `Dataset.scores(problems=None, vocabularies=None)` returns one row per child, indexed like
  `data`, with the columns `rules`, `U`, `T`, `TC`, `marked`, `M`, `flags`, `code`, `own_T`,
  `own_TC`, `own_T_marked` and `own_TC_marked`. A score not determined is `<NA>`, or `Ux` and `Mx`.
- `problems`, when given, is the problem table of a check. Every cell it names with the kind
  missing, wrong type, out of range or not in vocabulary is blanked before scoring (D-1). Rule
  problems name values that are themselves valid, and are not blanked (D-3).

### Report

- A second table, **Preview scores**, after the problems: Excel row, rules, U-score, T-score,
  TC-score, M-score, perturbation flags, quality code, and whether the child has problems. Each
  heading of a score links to its page of the scheme reference, the way a rule links to its entry.
- The summary gains "Quality scheme", linking the scheme's overview. The package version it
  already states is the version that made the scores (FR-006).
- The table is rendered by the same Jinja template. Its cells are prepared in one pass over the
  scores frame with `itertuples`, as the problems are now, to keep inside SC-004.

### Documentation

- `docs/user-guide/check.md`: the scores in the report.
- `docs/contributing/python-api.md`: `Dataset.scores`.
- `docs/reference/quality-scheme/index.md` and `worked-examples.md`: no longer say that no code
  computes the scores or runs the examples.
- `CONTEXT.md`: **Report**, **Quality scheme**, **Worked example** and **Preview score**.
- `CHANGELOG.md`: an **Added** entry.
- `docs/ROADMAP.md`: R6 loses its deliverable about disagreements with another implementation.

## Order

US-2 is built first, because the report reads its scores. US-1 follows on the same branch.

## Risks

- **Time.** The report's second table has 90,000 rows. If SC-004 fails, the first remedy is to
  render the rows without a Jinja loop per cell, and the second to omit children whose scores are
  all not determined from the table, which would need a re-gate because it changes US-1.
- **A page and an example that disagree.** The examples were written from the pages, but if the
  code meets an example it cannot satisfy without contradicting a page, it stops there and the
  disagreement is recorded, not coded around (FR-013).
