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
