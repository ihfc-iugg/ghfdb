# Tasks: Check the rules that relate several fields

**Input**: `plan.md`, `research.md`, `decisions.md` and `spec.md` in this directory.

**Tests**: every behaviour below is written test-first, per
`docs/contributing/standards/testing.md`. No test asserts wording or layout. Problems are asserted
as `(row, code, kind, rule)`.

**Order**: two stories. US1 is built in two groups and US2 in one. Each group leaves the tree green
and documents the public names it introduces.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: User Story 1 - A data assessor finds the children whose fields do not fit together (Priority: P1)

**Goal**: `ghfdb check` reports a rule problem for every child that breaks CF-1, CF-2 or CF-3,
with its Excel row, rule, fields and values, and still checks 90,000 children in under 15 seconds.

**Independent Test**: check a workbook seeded with one child breaking each rule and one child
satisfying it, and compare the rule problems with the ones seeded.

### Group 1 — the rules and their check

- [ ] T001 [US1] File one issue on this repository per question in `research.md` ("raised as an
  issue"), seven in all, each with the old rule or the paper's statement, what is unclear and the
  question for the data assessment team, labelled `needs-info`: the six rows marked "raised", and the confirmation of D-1, which
  says indirect methods are checked as borehole data until the team rules. Record their numbers in
  `decisions.md` under D-3. No code.
- [ ] T002 [US1] `ghfdb/qc/rules.py`: `Rule` (identifier, statement, source, reasoning,
  example, and `fields()`, `problems()`, `diagram()`), `RequiredWhen`, `AllowedWhen`, `Domain`,
  `Condition`, `Example`, the concept URI constants, `BOREHOLE`, `PROBE_SENSING`, and `RULES` holding
  CF-1, CF-2 and CF-3 with their statements, sources, reasoning and worked examples (plan.md,
  "Design"). `DatasetCheck` resolves every concept to its term on construction. Tests: `RULES`
  resolve against the test vocabularies, the domain rules read `C5`, `C31`, `C32` and `C6`, `C23`
  from the schema, and a concept that is not an allowed value of its field fails naming the rule
  (FR-005, FR-007, FR-011). One test resolves `RULES` against the vocabularies as currently
  published (`published_vocabularies`), so the suite fails when a concept is withdrawn (AS 2.6).
- [ ] T003 [US1] `RequiredWhen.problems()` and `AllowedWhen.problems()` on whole columns, with
  `DatasetCheck.holds()` and `DatasetCheck.rule_lines()`: condition held, not held, condition field
  empty, condition value not in the vocabulary, target value not in the vocabulary, a target field
  holding several values, a missing column, a condition field holding several values, and one child
  breaking CF-1 with two empty fields and CF-3 at once (AS 1.1–1.9, FR-001–FR-004). `related` names
  the condition field's code, column name and value. `DatasetCheck`: `Kind.RULE`, the `rule` and
  `related` columns, every rule's `problems()` after the field check, rule lines sorted after the
  field lines of their row. Existing check tests updated for the two new columns only.
- [ ] T004 [US1] `TestWorkedExamples` in `tests/test_qc/test_rules.py`: every rule's worked
  example over `valid_child` gives exactly its expected problem, and `valid_child` alone gives none
  (FR-009). `docs/reference/python-api.md` gains `automodule:: ghfdb.qc.rules`, which documents how
  to add a rule of a new kind.
- [x] T011 [US1] Name `Rule`, `RequiredWhen`, `AllowedWhen`, `Domain` and `Condition` on the Python
  API page, and give each subclass method its own docstring (the documentation check after group 1).
- [x] T012 [US1] Reword the reasoning of CF-1, CF-2 and CF-3 for the rule reference: no internal
  decision keys in published text, and CF-3 states the paper's condition.

### Group 2 — the command, the report and the speed

- [ ] T005 [US1] `Dataset.check(schema=None, rules=RULES)` and `ghfdb check` apply the
  rules in `RULES`; a concept no longer published gives status 2 with the rule named. The
  end-to-end test of a seeded workbook gains one child breaking each rule (SC-001). SC-004 is
  covered by the existing test of a correctly filled template in `tests/test_cli.py`.
- [ ] T006 [US1] `Report`: the rule identifier linked to its entry in the published rule
  reference, its statement, and the `related` value, for rule problems only (AS 1.10, FR-006).
  Tested on the report's cells.
- [ ] T007 [US1] The 90,000-child speed test (`tests/test_cli.py`, `TestSpeed`) applies the rules and still passes within SC-006,
  with one child in a hundred breaking a rule (AS 1.11, FR-012).
- [ ] T008 [US1] `docs/reference/check.md`: the rule problem kind and the two new columns.
  `CONTEXT.md`: amend **Cross-field rule** and the **rule** problem kind, add the domain
  read from the exploration method and the note under **missing**. `Dataset.check` and `Report`
  docstrings list the two new columns. `CHANGELOG.md`: Added, Changed (two problem columns) and **Scheme changes** (CF-1,
  CF-2, CF-3) (FR-013).

---

## Phase 2: User Story 2 - A data assessor looks up why a rule exists (Priority: P2)

**Goal**: every rule the check applies has an entry in the documentation with its source,
reasoning, diagram and worked example, reachable from its identifier, and the field reference
lists each field's rules.

**Independent Test**: take any rule from a report, find its entry by identifier, and confirm it
names a source, gives its reasoning, has a diagram and an example matching what the check reports.

### Group 3 — the rule reference

- [ ] T009 [US2] `docs/extensions/rule_reference.py` and `templates/rule_reference.md.jinja`
  render `docs/reference/rules.md` from `RULES`: an introduction to the two kinds and the
  domain mapping with D-1 cited, then one entry per rule, anchored by its identifier, with its
  statement, fields (linked to their field reference entries), source, reasoning, the Mermaid flowchart from its
  `diagram()`, with node labels quoted, and the worked example. The source lookup gains `fuchs-2023-table-4`. A "Rules under discussion" section links the issues filed in T001. Added to
  `docs/reference/index.md`. Tests: every rule in `RULES` has exactly one entry and no entry has no
  rule; every entry has each part (AS 2.1–2.3, FR-008).
- [ ] T010 [US2] `field_reference.py`: each field's entry lists the identifiers of the rules that
  relate it, linked to their entries (AS 2.5, FR-010). Test: every rule appears under every field
  it relates, and under no other. The documentation builds with `-W`.

---

## Dependencies

- T001 first: the rule reference links the issues it files.
- T002 → T003 → T004 → T005 → T006, T007, T008.
- T009 needs T002. T010 needs T009.
