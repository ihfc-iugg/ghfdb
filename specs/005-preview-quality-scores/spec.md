# Feature Specification: Preview quality scores for each child

**Feature Branch**: `005-preview-quality-scores`

**Created**: 2026-11-06

**Status**: Draft

**Serves**: G3 · **Roadmap**: R6 · **Depends on**: FS-003, the workbook check ([#21](https://github.com/ihfc-iugg/ghfdb/issues/21)), delivered; R5, the quality scheme written down ([#37](https://github.com/ihfc-iugg/ghfdb/issues/37)), delivered

**Input**: [#46](https://github.com/ihfc-iugg/ghfdb/issues/46), "Preview quality scores for each
child in the check report": when an assessor checks a workbook, the report should also give each
child its preview quality score: the U-score, the T-score and TC-score under the probe-sensing or
the borehole and mine rules, the M-score with its missing-information mark, the perturbation flags
and the quality code. The scores follow the scheme exactly as the reference documentation writes
it down, and every worked example gives exactly its expected scores. A developer can get the same
scores for a dataset from Python. The quality code a parent inherits from its children is a
separate piece of work.

## Overview

The check (FS-003, FS-004) reports what is wrong with a workbook. This feature adds what the
workbook's children would score. A data assessor runs the same command as before, and the report
now also has a table of **preview scores**: one row per child, by its Excel row, with its U-score,
T-score, TC-score, M-score, perturbation flags and quality code.

The scores are computed from the quality scheme exactly as the reference documentation sets it
out. The scheme's worked examples are the proof: every one of them, except those for a parent's
inherited code, is run by the test suite and must give exactly its expected scores. The scheme is
the only authority. Where the code and a page disagree, one of them is wrong, and the fix changes
them together.

A developer gets the same scores from Python, for a dataset read from a workbook or built in code.

**Out of scope**

- The quality code a parent inherits from its relevant children (R10). The worked examples for it
  stay in the scheme and are not run yet.
- Numbered, citable releases of the scheme (R8). Until they exist, the report names the package
  version the scores were made with.
- Writing the scores into a copy of the workbook. The report is where they go for now.
- Settling the open questions of the scheme that the corrected paper leaves open. The scheme
  follows Fuchs et al. (2023) as corrected in 2026, and a later ruling changes a page, its worked
  examples and the code together.
- Any comparison with scores computed elsewhere.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A data assessor previews the quality score of every child (Priority: P1)

A data assessor checks a workbook as before. The report now also lists every child with its preview
scores: the U-score, the T-score and TC-score and which rules gave them, the M-score with its
missing-information mark, the perturbation flags and the quality code. Before uploading, the
assessor can see which children will score poorly, and that a mark means information they could
still add.

**Why this priority**: This is the feature. An assessor has no other way to see what a workbook
will score before it is submitted.

**Independent Test**: Check a workbook whose children are the worked examples that describe a
whole child, and compare the scores in the report with each example's expected scores.

**Acceptance Scenarios**:

1. **Given** a workbook, **When** it is checked, **Then** the report gives every child its U-score,
   T-score, TC-score, M-score, perturbation flags and quality code, against the child's Excel row.
2. **Given** a child, **When** its scores are reported, **Then** the report says whether the
   probe-sensing rules, the borehole and mine rules or no rules gave its T-score and TC-score.
3. **Given** a child for which a score cannot be made, **When** its scores are reported, **Then**
   the score is shown as not determined, as the scheme writes it, and never as 0.
4. **Given** a child one of whose scored inputs is empty, **When** its scores are reported,
   **Then** its M-score carries the missing-information mark.
5. **Given** a child that also has problems, **When** its scores are reported, **Then** it is still
   scored, any input with a problem is scored as if it were empty, and its row of scores says the
   child has problems.
6. **Given** a workbook with no problems, **When** it is checked, **Then** every child is scored
   and the report still says the workbook has no problems.
7. **Given** a report, **When** an assessor reads its scores, **Then** it names the package version
   that made them and shows where each part of the scheme is documented.
8. **Given** a workbook of 90,000 children with every field filled, **When** it is checked, **Then**
   the check, the scores and the report are finished within the time set in SC-004.

---

### User Story 2 - A developer scores a dataset from Python (Priority: P2)

A developer working with GHFDB data in Python scores a dataset, read from a workbook or built in
code, and gets the same scores the report shows, one row per child. The scores of a child's
gradient and conductivity on their own, before the child's corrections apply, are available the
same way.

**Why this priority**: Every score in the report comes from this, and it lets other tools use the
scheme without reading a report.

**Independent Test**: Run every worked example through the Python interface and compare each
result with the example's expected scores.

**Acceptance Scenarios**:

1. **Given** a dataset, **When** a developer scores it, **Then** they get one row per child, with
   the same U-score, T-score, TC-score, M-score, mark, perturbation flags and quality code the
   report shows for that child.
2. **Given** any worked example other than an inherited code's, **When** its inputs are scored,
   **Then** the result is exactly its expected scores. The worked examples are run by the test
   suite, so an example that stops matching fails.
3. **Given** a child, **When** a developer asks for its own scores, **Then** they get the T-score of
   its gradient and the TC-score of its conductivity before the child's corrections apply, as the
   worked examples of a measurement expect.
4. **Given** a dataset whose values have not been checked, **When** a developer scores it, **Then**
   it is scored without being checked first, and an input that is not a value the scheme knows is
   scored as if it were empty.

---

### Edge Cases

- A child whose exploration method is empty, not in the vocabulary, or selects no rules: its
  T-score, TC-score and M-score are not determined, and its U-score and perturbation flags are
  still scored.
- A heat-flow value or uncertainty that is empty or zero: the U-score is not determined.
- A field holding several values: each value is scored and the poorest counts, as the scheme says.
- A workbook from an earlier upload template that has no column for a scored field: the column
  problem is reported as before, and the field is scored as empty for every child.
- A workbook with no children: the report says there is nothing to score.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The check MUST score every child of the workbook in the same run, and the report MUST
  give each child's U-score, T-score, TC-score, M-score with its missing-information mark,
  perturbation flags and quality code against its Excel row. (US1)
- **FR-002**: Every score MUST follow the quality scheme as the reference documentation writes it
  down, which follows Fuchs et al. (2023) with its 2026 corrigendum and corrected tables,
  including which rules apply, the empty and unspecified inputs, the missing-information
  mark, not determined and several values in one field. (US1, US2)
- **FR-003**: The report MUST say which rules gave each child's T-score and TC-score, or that none
  applied. (US1)
- **FR-004**: A score that cannot be made MUST be shown as not determined, as the scheme writes it,
  and never as 0. (US1, US2)
- **FR-005**: A child with problems MUST still be scored. An input with a problem MUST be scored as
  if it were empty, and the child's row of scores MUST say that it has problems. (US1)
- **FR-006**: The report MUST name the package version that made its scores and show where each
  part of the scheme is documented. It MUST still hold no copy of the workbook's data beyond the
  values its problems name. (US1)
- **FR-007**: A developer MUST be able to score a dataset from Python and get one row per child with
  the same scores the report shows. (US2)
- **FR-008**: A developer MUST be able to get a child's own scores: the T-score of its gradient and
  the TC-score of its conductivity before the child's corrections apply. (US2)
- **FR-009**: Every worked example other than an inherited code's MUST be run by the test suite and
  MUST produce exactly its expected scores. (US2)
- **FR-010**: Every vocabulary term the scoring reads MUST be referred to by its concept's
  identifier and read from the IHFC Controlled Vocabularies as currently published, as the
  cross-field rules do. Loading the scoring MUST fail, naming the concept, when one is no longer
  published. (US1, US2)
- **FR-011**: The time to check and score a workbook MUST meet SC-004, and MUST be measured by the
  test suite. (US1)
- **FR-012**: The documentation MUST describe the scores in the report and the Python interface,
  and the scheme pages and glossary MUST no longer say that the package computes no score. (US1,
  US2)
- **FR-013**: Changing how a score is computed MUST change the scheme's page, its worked examples
  and the code together, and MUST be recorded in `CHANGELOG.md` under **Scheme changes**. (US2)

### Key Entities

- **Preview score**: the scores of one child: its U-score, T-score, TC-score, M-score with its
  mark, perturbation flags, quality code and the rules that applied.
- **Own score**: the T-score of a child's gradient or the TC-score of its conductivity before the
  child's corrections apply.
- **Worked example**: a set of inputs with the scores the scheme expects for them, run by the test
  suite.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every worked example other than the 21 for an inherited code passes, with exactly
  its expected scores.
- **SC-002**: A workbook whose children are the worked examples that describe a whole child is
  checked, and the report gives each child exactly its example's expected scores.
- **SC-003**: For every child of a checked workbook, the scores in the report and the scores from
  the Python interface are the same.
- **SC-004**: The 90,000-child workbook of FS-003's SC-006 is checked, scored and reported in under
  15 seconds, on the machines the test suite runs on.
- **SC-005**: An assessor given a child's quality code in a report can find, from the report and
  the documentation alone, the page that explains each part of it.

## Clarifications

### Session 2026-11-06

- Q: Do the scores have to agree with any other implementation? → A: No. The scheme as the
  documentation writes it is the only authority, and the worked examples are its test. Integrated
  in the Overview and the out-of-scope list.
- Q: Where do the scores go? → A: In the report. Writing them into a copy of the workbook is
  later work. Integrated as FR-001 and the out-of-scope list.
- Q: Which scheme version does the report name? → A: None yet: numbered scheme releases are R8.
  The report names the package version and links the scheme pages. Integrated as FR-006 and
  Acceptance Scenario 1.7.
- Q: Is a child with problems scored? → A: Yes. An input with a problem is scored as if it were
  empty, so its criterion takes the largest penalty and the mark is set, and the row says the child
  has problems (`decisions.md`, D-1). Integrated as FR-005 and Acceptance Scenario 1.5.
- Q: Do the open questions of the scheme block this? → A: No. The code follows the pages as they
  read today (`decisions.md`, D-2). Integrated in the out-of-scope list.
- Q: Are a measurement's own scores part of this? → A: In Python only, because 38 worked examples
  assert them. The report shows only the child's scores. Integrated as FR-008 and Acceptance
  Scenario 2.3.
- Q: Does scoring a dataset from Python check it first? → A: No. Scoring reads what it is given,
  and a value the scheme does not know is scored as empty, so scoring never depends on the check.
  Integrated as Acceptance Scenario 2.4.

## Assumptions

- Everything a child's scores need is on the child's own row of the workbook, because the parent's
  fields are repeated on every child.
- How the report lays out the scores, and how it shows where each part of the scheme is documented,
  is settled at planning. It works offline, as the report does.
- The glossary's entries for **report**, **quality scheme**, **worked example** and **preview score**
  change to say that the package computes the scores.
- Roadmap item R6 loses its deliverable about disagreements with another implementation, in this
  feature's pull request.
