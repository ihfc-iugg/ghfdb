# Implementation Plan: Preview quality scores for each child

**Branch**: `005-preview-quality-scores` | **Spec**: [spec.md](spec.md) | **Research**: [research.md](research.md)

## Summary

The scoring declares each criterion of the quality scheme once, as data, and a small engine
scores every child of a dataset on whole columns from those declarations. `Dataset.scores()`
returns one row per child. The check command passes the problems it found, so their cells are
scored as empty, and the report gains a second table of preview scores. The scheme pages render
each criterion's penalty table from the same declaration, and the worked examples are the test of
the scoring.

The scheme follows Fuchs et al. (2023) as corrected in 2026: the corrigendum (Tectonophysics 934,
231226) and its corrected Tables 1 to 5 and Appendices A and B.

## Technical context

- Python 3.12 and 3.13, pandas and numpy, frictionless, Jinja2 and markupsafe for the report.
- Tests: pytest, mirroring the source tree (`docs/contributing/standards/testing.md`). The
  vocabularies come from the cached release the existing tests use (`vocabularies_cached`).
- Performance: SC-004's 15 s for the 90,000-child workbook is a target, measured by
  `tests/test_cli.py::TestSpeed`. Accuracy and clear code come first (D-15).

## Constitution check

- **Simplicity.** A criterion is a declaration, not a method. Three kinds of penalty table cover
  every criterion of the scheme, and only the parts of the scheme that are procedure (routing, the
  waivers, the borehole depth gate, choosing the borehole case, the pT agreement) are code.
- **Every rule traceable.** Each declaration names its source in the corrected paper, and the
  scheme page renders its table from the declaration, so the page and the code cannot disagree.
- **Report-only.** The workbook is never changed. The report holds the scores and no copy of the
  data.

## Design

### Column names, never field codes

`ghfdb/fields/names.py` holds `Field`, a `StrEnum` generated from `ghfdb/fields/schema.json`: one
member per field, named by the field's published column name, whose value is the field's code
(`Field.tc_location == "C42"`). Python source in `ghfdb/` refers to a field only through `Field`.
The data stays keyed by code (ADR 0005), so a corrected column name changes the member's name and
the type checker finds every use, while workbooks, worked examples and the dataset keep their
keys. `python -m ghfdb.fields.names` writes the module, and a test fails when the file differs
from what the schema generates.

### Modules

| Module | Holds |
|---|---|
| `ghfdb/fields/names.py` | `Field`, generated |
| `ghfdb/qc/penalties.py` | `Penalty`, and the three kinds of table: `Bands` (a number against ordered edges), `Classes` (a term against groups of concepts) and `Cases` (rows of conditions on several fields, the poorest matching row winning). Each scores whole columns and lists its rows for the documentation |
| `ghfdb/qc/criteria.py` | `Criterion`: an identifier (the worked examples' criterion identifier, such as `probe-t.penetration`), the fields it reads, its table, what an empty input scores, and its source. `CRITERIA` lists every one. The concepts the scheme reads are collected from the declarations, and resolved and checked against the vocabularies on load (FR-010) |
| `ghfdb/qc/uncertainty.py` | The U-score |
| `ghfdb/qc/probe.py` | The probe-sensing declarations, the two waivers, and the groups of concepts that probe and borehole criteria share. A declaration names a concept by its local name in the vocabulary of the field it sits under, such as `"LOGeq"` under `T_method_top` |
| `ghfdb/qc/borehole.py` | The borehole and mine declarations, the depth gate, the choice of case and the pT agreement with the in-situ correction |
| `ghfdb/qc/scores.py` | `Scores`: routing once, the T-score and TC-score as totals of their criteria, the M-score, not determined, the perturbation flags, the quality code and the table of scores |

The term lookup and the number parsing are shared with the check: `ghfdb.fields` resolves the local
names of concepts to the terms a field accepts, and one function parses a number cell for both the check and
the scoring. Constants such as the rounding and the output columns are defined once and imported
where they are needed, including by the report and the documentation extension.

### Shapes

- A criterion scores to a `Penalty`: two aligned Series over the children, the penalty and
  whether it sets the mark. A T-score or TC-score is 1.0 plus the sum of its criteria's
  penalties, rounded to three places, marked when any criterion is.
- A field with several values is held exploded, one row per value with the child's index, and a
  criterion keeps the poorest value per child. Several values reach the scoring only from a
  dataset built in code, as a Python list in the cell (D-6).
- `Dataset.scores(problems=None, vocabularies=None, schema=None)` returns one row per child,
  indexed like `data`, with the columns `rules`, `U`, `T`, `TC`, `marked`, `M`, `flags`, `code`,
  `own_T`, `own_TC`, `own_T_marked` and `own_TC_marked`. A score not determined is `<NA>`, or `Ux`
  and `Mx`.
- `problems`, when given, is the problem table of a check. Every cell it names with the kind
  missing, wrong type, out of range, not in vocabulary or rule is blanked before scoring (D-1,
  D-3).

### Report

- A second table, **Preview scores**, after the problems: Excel row, rules, U-score, T-score,
  TC-score, M-score, perturbation flags, quality code, and whether the child has problems. One
  list of (heading, column, scheme page) drives the headings, the cells and the links.
- The summary gains "Quality scheme", linking the scheme's overview, and names the package version
  that made the scores (FR-006).
- The cells are plain strings prepared in one pass over the scores frame, and the template writes
  each row with one `join`.

### Documentation

- The scheme pages render each criterion's penalty table from its declaration with a directive of
  the documentation extension, the way the rule reference renders the cross-field rules (ADR
  0006). Each page's diagram shows the structure of its criteria, with no penalty values.
- The scheme pages cite the corrected paper. The departures page lists only where the scheme still
  differs from it.
- `docs/contributing/python-api.md`: `Field`, the criteria and `Dataset.scores`.
- `docs/user-guide/check.md`, `CONTEXT.md`, `README.md`, `CHANGELOG.md` and `docs/ROADMAP.md` as
  before, and every change to a score under **Scheme changes**.

## Order

1. `Field` and the shared concepts module, which also bring the concept identifiers in line with
   the vocabularies as now published, so the rebased branch is green again.
2. The criteria engine and the declarations, with the current scheme unchanged: every worked
   example passes before and after.
3. The changes of the corrigendum, the scheme pages and the departures page.
4. The tests and the report tidied, and the Python API page.

## Risks

- **Time.** The report's second table has 90,000 rows, and CI runs the suite under coverage. A
  run over the 15 s target is not a reason to make the code less clear (D-15).
- **A page and an example that disagree.** If the code meets an example it cannot satisfy without
  contradicting the corrected paper, it stops there and the disagreement is recorded, not coded
  around (FR-013).
