# Research: Preview quality scores for each child

## Assumptions checked

- **The check command and its report work on this repository.** A blank upload template written
  with `ghfdb.template.UploadTemplate().write()` and checked with `ghfdb check` reports "0
  children, 0 problems" and writes `t.report.html` beside the workbook. Checked 2026-11-06 on
  origin/main at ef739c3.
- **Every worked example has inputs keyed by field code and expected scores.**
  `ghfdb/qc/worked_examples.json` holds 205 examples: 167 scored as a child and 38 as a
  measurement on its own. 21 of them are for a parent's inherited code (`part: inheritance`),
  which leaves 184 for this feature. The M-score examples take a T-score and TC-score as inputs
  rather than field codes.
- **The cross-field rules already read vocabulary terms by concept identifier.** `ghfdb/qc/rules.py`
  names every term by its concept's URI and fails to load when one is not published, which is the
  pattern FR-010 asks the scoring to follow.
- **The time budget has room, but not much.** `tests/test_cli.py::TestSpeed` checks the
  90,000-child workbook of `tests/conftest.py::large_workbook` in 7.9 s on this machine against
  its 15 s limit (run 2026-11-06). Scoring and a second table in the report have to fit in the
  remaining 7 s.

## The worked examples, by what each one asserts

| Part | Examples | Asserts |
|---|---|---|
| routing | 11 | which rules apply |
| u-score | 17 | U |
| probe-t, borehole-t | 40 | T and, mostly, the mark |
| probe-tc, borehole-tc | 60 | TC and, mostly, the mark |
| m-score | 15 | M, from a given T, TC and mark |
| perturbation-flags | 18 | flags |
| child | 23 | U, T, TC, M, flags, code, mark, and own scores for 19 of them |
| inheritance | 21 | out of scope (R10) |

38 of the T and TC examples have `scoring: measurement`: the expected score is the measurement's
own score, which applies none of the child's corrections. The others are scored as a child. The
own scores differ from the child's in three places only, all named on the scheme's overview page
under "Scores of a child and of its measurements": the probe tilt waiver (`C12`), the probe
water-depth waiver (`C17`), and the borehole pT criterion, which needs the in-situ correction
`C11` to agree for a child and scores the pT conditions alone for a measurement (DEP-15).

## How the scheme reads its inputs

- **Numbers.** `C1`, `C2`, `C4`, `C5`, `C6`, `C23`, `C37`, `C47` and `P6` are numbers in the field
  schema. A dataset holds every field as text (`ghfdb/dataset.py`), so scoring parses them, and a
  cell that does not parse is not a value the scheme knows.
- **Terms.** Every other input is a vocabulary field. The terms the scheme names are concepts in
  the IHFC vocabularies of those fields (`ghfdb/fields/schema.json`, each field's
  `vocabulary.scheme`), so they are named by URI and resolved to the terms of the vocabularies as
  published, through `ghfdb.fields.allowed_values`, as `DatasetCheck.resolve` does for the rules.
- **Several values.** A field with a `separator` in the schema can hold several values. The check
  already splits them (`DatasetCheck.each_value`, `ghfdb/qc/check.py:366`). The scheme scores each
  value and takes the poorest (overview, "Several values in one field").
- **Empty, unspecified, unmatched.** The overview's section "Empty, unspecified and the
  missing-information mark" gives the three outcomes every criterion follows, with the named
  exceptions on each page.

## Approach

Each criterion is scored on whole columns, the way the cross-field rules work
(`ghfdb/qc/rules.py`, "working on whole columns"), so 90,000 children are scored with a few dozen
pandas operations rather than 90,000 Python calls per criterion. A criterion returns its penalty
and its mark for every child. A table of penalties keyed by concept URI is a plain mapping
resolved to terms once, at load.

Considered and not taken: scoring one child at a time with plain functions. It reads closest to
the pages but costs a Python call per child per criterion, roughly 20 criteria × 90,000 children,
which would use most of the remaining time budget before the report is written.

## What already exists

| New piece | Where the search stopped |
|---|---|
| Resolving concept URIs to the terms a field accepts | This repo: `ghfdb.fields.allowed_values` and `MissingSchemeError`, as used by `DatasetCheck.resolve`. Reused, not rewritten |
| Splitting a cell into its several values | This repo: `DatasetCheck.each_value`. Made a module function that both the check and the scoring call |
| Blank-cell test | This repo: `DatasetCheck.blank`. Reused the same way |
| Exploration-method domains | This repo: the domain concepts in `ghfdb/qc/rules.py` (`DRILLING`, `PROBING_ONSHORE` and the rest). Imported, not restated |
| Reading the worked examples | This repo: `tests/test_qc/test_worked_examples.py` loads the file through `importlib.resources`. The new tests load it the same way |
| The report page and its table rendering | This repo: `ghfdb/qc/report.py` and `report.html.jinja`. Extended with a second table |
| Penalty tables, criteria, the M-score classes, the flags, the quality code | New code. Nothing installed implements the GHFDB quality scheme. The old checking tool is a separate, superseded codebase and is not a dependency (R9) |

## Not adopted

- The `portal_tests` entries and the "as the GHFDB portal applies it" wording in the worked
  examples file and the scheme pages are left as they are. They belong to the scheme's own record,
  and this feature scores against the examples without comparing with anything else.
