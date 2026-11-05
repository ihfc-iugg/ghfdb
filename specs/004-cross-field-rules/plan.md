# Implementation Plan: Check the rules that relate several fields

**Branch**: `004-cross-field-rules` · **Spec**: `spec.md` · **Research**: `research.md` ·
**Decisions**: `decisions.md`

## Summary

The cross-field rules are kept in one packaged file, `ghfdb/qc/rules.json`, read by the check and by
the documentation build, in the same way as the field schema. Each rule is one of two kinds,
*required when* and *allowed when*, and names its concepts by URI, which are turned into terms
through the same `Vocabularies` the field schema uses. After the field check, `DatasetCheck` applies
every rule to whole columns and adds a line of kind `rule` per broken rule to the problem table,
with two new columns, `rule` and `related`. The documentation gains a rule reference rendered from
the same file, with a generated diagram per rule, and every rule's worked example runs as a test.

Three rules are checked in this feature (`research.md`):

| Id | Rule | Kind | Source |
|---|---|---|---|
| CF-1 | A child whose exploration method is borehole or mine data has every field mandatory for that domain filled: `C5`, `C31`, `C32` | required when | Fuchs et al. (2023), Table 4 (obligation and domain of the five fields), with D-1 for the domain of each exploration method. The fields are read from the field schema's obligation and domain |
| CF-2 | A child whose exploration method is probe sensing has every field mandatory for that domain filled: `C6`, `C23` | required when | as CF-1 |
| CF-3 | The thermal conductivity location (`C42`) is `[Literature or unspecified]` only if the thermal conductivity source (`C41`) is `[Assumed from literature]` | allowed when | Fuchs et al. (2023), Appendix A, field `C42` |

Seven questions are raised as issues for the data assessment team (`research.md`, first section).

## Technical Context

- **Language**: Python 3.12+, pandas 3 (Article XV).
- **Dependencies added**: none.
- **Storage**: `ghfdb/qc/rules.json`, packaged with `ghfdb`.
- **Testing**: pytest. Vocabularies are served from the test cache the field and check tests
  already use (`tests/conftest.py`).
- **Performance**: SC-006, measured by the existing 90,000-child test, which now applies the rules.

## Constitution Check

| Article | How the plan meets it |
|---|---|
| I Testing | Every behaviour test-first. Worked examples are tests. |
| II Simplicity, III Anti-abstraction | Two rule kinds, both needed now. No rule engine, plugin registry or base class. |
| VI Documentation | Rule reference, check reference and field reference updated in the same pull request. |
| VII Dependency discipline | No new dependency. |
| IX Every rule names its source | `source` is a required key of every rule; the load fails without it. |
| X Rules, examples and code change together | One record per rule drives check, documentation and example test. `CHANGELOG.md` gains a **Scheme changes** entry. |
| XI Vocabulary from the published vocabularies | Concepts by URI, read through `Vocabularies`. No term in code or `rules.json`. |
| XII Report, never modify | Unchanged: the rules read the `Dataset`, never the workbook. |
| XIII Whole columns | Masks over columns; no row loop. |
| XIV Compatibility | Two problem columns added; nothing removed or renamed. Recorded in `CHANGELOG.md`. |

## Project Structure

### Documentation (this feature)

```text
specs/004-cross-field-rules/
├── spec.md
├── decisions.md
├── research.md
├── plan.md
└── tasks.md
```

### Source code

```text
ghfdb/qc/
├── rules.json          new: domains and rules
├── rules.py            new: Rule, Domain, load_rules
├── check.py            Kind.RULE; PROBLEM_COLUMNS gains rule, related; rule_problems()
├── report.py           rule and related cells, link to the rule's entry
└── templates/report.html.jinja
ghfdb/dataset.py        Dataset.check takes the rules
ghfdb/cli.py            loads the rules with the schema
docs/extensions/
├── rule_reference.py   new: renders docs/reference/rules.md
├── field_reference.py  lists the rules involving each field
└── templates/rule_reference.md.jinja
docs/reference/rules.md, check.md, python-api.md, index.md
CONTEXT.md, CHANGELOG.md
tests/test_qc/test_rules.py           new, with TestWorkedExamples
tests/test_docs/test_extensions/test_rule_reference.py   new
```

## Design

### `ghfdb/qc/rules.json`

```json
{
  "domains": {
    "B": {"field": "P12", "concepts": ["…/exploration-methods/drilling", "…"], "source": "fuchs-2023-table-4", "ruling": "D-1"},
    "S": {"field": "P12", "concepts": ["…/exploration-methods/probing_onshore", "…"], "source": "fuchs-2023-table-4", "ruling": "D-1"}
  },
  "rules": [
    {"id": "CF-1", "kind": "required when", "domain": "B", "statement": "…", "source": "…", "reasoning": "…",
     "example": {"values": {"P12": "[Drilling]", "C5": ""}, "problems": [{"code": "C5", "related": "P12 [Drilling]"}]}},
    {"id": "CF-3", "kind": "allowed when",
     "when": {"field": "C42", "concepts": ["…/conductivity-location/…"]},
     "then": {"field": "C41", "concepts": ["…/conductivity-sources/…"]},
     "statement": "…", "source": "fuchs-2023-appendix-a", "reasoning": "…", "example": {…}}
  ]
}
```

- A *required when* rule names a `domain`, whose required fields are read from the field schema
  (obligation `M`, that domain only). A form with its fields listed is added with the first agreed
  rule that needs it, not now (Article III).
- `source` uses the field schema's source keys so both files cite sources the same way, and the
  documentation resolves them with the same lookup (`field_reference.py`, `sources`). The lookup
  gains `fuchs-2023-table-4`, and `decision:004:D-n` for a ruling recorded in this feature's
  `decisions.md`. The field schema's `decision:D-n` keys point at FS-001's decisions, and this
  feature's numbers would otherwise collide with them.
- `example.values` holds only the fields the rule reads. A vocabulary field's value is given as its
  concept URI and resolved to the term at load with the rule's own lookup, so no term is typed into
  the file (FR-005). Number and text values are plain. The expected `related` is derived from the
  resolved term. The test lays the values over the `valid_child` fixture (`tests/conftest.py`).

### `ghfdb/qc/rules.py`

- `Domain` and `Rule`: frozen dataclasses. `Rule.fields` lists every field the rule relates.
- `load_rules(schema, vocabularies, path=None) -> tuple[Rule, ...]`: reads the file, turns every
  concept URI into its term with `ghfdb.fields.schema.allowed_values(field, vocabularies)` for the
  field the concept is used in, as a URI-to-term map, and for a domain rule reads the required
  fields from the schema. A URI not among that field's allowed values (a collection, or a concept
  of another scheme) fails. Raises `MissingSchemeError` naming the
  rule and the URI when a concept is not in its scheme (FR-011), and `KeyError` naming the rule for
  a missing key or an unknown field code.
- `rules.py` holds no check code. The check is `DatasetCheck.rule_problems()`, below.

### `ghfdb.qc.check`

- `Kind.RULE = "rule"`. `PROBLEM_COLUMNS` gains `rule` and `related`, empty for the other kinds.
- `DatasetCheck(data, schema, rules=())`: `problems()` builds the field problems, then
  `rule_problems()`, and sorts both by row and then field order, rule lines after the field lines
  of the same row.
- `rule_problems()` needs no record of the field problems: it reads the same facts from the cells,
  as column masks (Article XIII).
  - The condition holds on a row when every value of the condition cell, split with `each_value`,
    is in the field's allowed values and at least one is in the rule's terms. An empty cell, or
    one with a value not in the vocabulary, never holds.
  - *required when*: on those rows, one line of kind `rule` per required field that is empty.
  - *allowed when*: on those rows, the target split with `each_value`. A value in the field's
    allowed values and outside the rule's allowed terms is one line. A value not in the vocabulary
    already has its own problem and is skipped (FR-004).
  - A field with no column in the workbook: the rule is skipped, and the column problem stands.
  - `related` is the condition field's code, published column name and the value found.

### `Dataset.check` and `ghfdb.cli`

- `Dataset.check(schema=None, rules=None)`: without rules, the packaged rules for the schema. Its
  docstring, and `Report`'s, list the two new columns.
- `ghfdb check` loads the rules with the schema; a `MissingSchemeError` from either gives status 2,
  as now.

### `ghfdb.qc.report.Report`

- Each rule problem shows its identifier, linked to
  `https://ihfc-iugg.github.io/ghfdb/reference/rules.html#<id>`, the identifier lowercased, and its
  statement. The `related`
  value is shown beside the field's own value. Layout is settled by eye at the walkthrough; the
  tests assert the cells, never the wording.

### Documentation

- `docs/extensions/rule_reference.py` renders `docs/reference/rules.md` while the documentation
  builds: one entry per rule with its identifier as anchor, statement, fields related (linked to
  their field reference entries), source, reasoning, a Mermaid flowchart generated from the rule's
  kind and fields, and the worked example as a table of values and the problem expected. A
  section before the entries explains the two kinds and the domain mapping, with D-1 cited.
- The source lookup's `decision:004:D-n` branch is matched before the existing `decision:` one,
  which would otherwise link FS-001's decisions. Node labels in the flowcharts are quoted.
- `field_reference.py` adds "Rules" to each field's entry, listing the identifiers of the rules
  that relate the field.
- `docs/reference/check.md`: the rule problem kind and the two new columns.
- `docs/reference/python-api.md`: `automodule:: ghfdb.qc.rules`.
- `CONTEXT.md`: amend **Cross-field rule** (identifier, source, an example this feature checks)
  and the **rule** problem kind, add that the domain is read from the exploration method, and the
  note under **missing**.
- `CHANGELOG.md`: the feature under Added, the two problem columns under Changed, the three rules
  under **Scheme changes**.

### Issues for the data assessment team

Filed on this repository at the start of the build, before any code, one per question in
`research.md`. Each states the old rule or the paper's statement, what is unclear and the question
to settle, and is labelled `needs-info`. The rule reference lists them under "Rules under
discussion", linked, so a reader can see what is not yet checked and why.

## Testing approach

- `tests/test_qc/test_rules.py`: `load_rules` on the packaged file against the test vocabularies;
  a missing concept, a missing source and an unknown field each fail with the rule named. Each
  kind on a small DataFrame: condition held and broken, condition not held, condition field empty,
  condition value not in the vocabulary, target value not in the vocabulary, a target field holding several values, a missing column.
  Also: a condition field holding several values, and one child breaking CF-1 with two empty
  fields and CF-3 at once, giving three rule lines after its field lines.
- `TestWorkedExamples` in `tests/test_qc/test_rules.py`: one parametrised test over every packaged
  rule: its example over `valid_child` gives exactly the expected rule problem, and `valid_child`
  alone gives none. A rule with no example fails.
- `tests/test_qc/test_check.py`: the end-to-end test of a seeded workbook gains one child per rule.
  SC-004 is already shown by the test of a correctly filled template in `tests/test_cli.py`.
- The 90,000-child speed test (`tests/test_cli.py`, `TestSpeed`) applies the rules, and its
  `large_workbook` fixture seeds one child in a hundred breaking a rule (SC-006).
- `tests/test_docs/test_extensions/test_rule_reference.py`: every packaged rule has an entry, no
  entry exists without a rule, every entry has a source, reasoning, diagram and example; the field
  reference lists each rule under every field it relates.
- No test asserts wording or layout. Problems are asserted as `(row, code, kind, rule)`.

## Complexity Tracking

None. Nothing in this plan departs from the constitution.
