# Implementation Plan: Check the rules that relate several fields

**Branch**: `004-cross-field-rules` · **Spec**: `spec.md` · **Research**: `research.md` ·
**Decisions**: `decisions.md`

## Summary

The cross-field rules are declared in Python, in `ghfdb.qc.rules`: a frozen `Rule` dataclass with a
`problems()` method, and two subclasses, `RequiredWhen` and `AllowedWhen`, that implement it a
column at a time. A rule names its concepts by URI, and they are turned into terms through the field
schema's allowed values. After the field check, `DatasetCheck` calls every rule's `problems()` and
adds a line of kind `rule` per broken rule to the problem table, with two new columns, `rule` and
`related`. The documentation gains a rule reference generated from the same rules, with a diagram
per rule from its `diagram()` method, and every rule's worked example runs as a test.

Three rules are checked in this feature (`research.md`):

| Id | Rule | Kind | Source |
|---|---|---|---|
| CF-1 | A child whose exploration method is borehole or mine data has every field mandatory for that domain filled: `C4`, `C5`, `C31`, `C32` | required when | Fuchs et al. (2023), Table 4 (obligation and domain of the five fields), with D-1 for the domain of each exploration method. The fields are read from the field schema's obligation and domain |
| CF-2 | A child whose exploration method is probe sensing has every field mandatory for that domain filled: `C6`, `C23` | required when | as CF-1 |
| CF-3 | The thermal conductivity location (`C42`) is `[Literature or unspecified]` only if the thermal conductivity source (`C41`) is `[Assumed from literature]` | allowed when | Fuchs et al. (2023), Appendix A, field `C42` |
| CF-4 | A child whose temperature method at the top (`C31`) or at the bottom (`C32`) is `[EGRT]` has the thermal conductivity method (`C43`) `[Probe - pulse technique]` | allowed when, with the second condition as an alternative | Fuchs et al. (2025), description of version 2026.03 of the submission template, section 6.1 |

Seven questions are raised as issues for the data assessment team (`research.md`, first section).

## Technical Context

- **Language**: Python 3.12+, pandas 3 (Article XV).
- **Dependencies added**: none.
- **Storage**: none. The rules are a Python module.
- **Testing**: pytest. Vocabularies are served from the test cache the field and check tests
  already use (`tests/conftest.py`).
- **Performance**: SC-006, measured by the existing 90,000-child test, which now applies the rules.

## Constitution Check

| Article | How the plan meets it |
|---|---|
| I Testing | Every behaviour test-first. Worked examples are tests. |
| II Simplicity, III Anti-abstraction | One base class with two subclasses, both used now. The base class replaces a branch on the rule's kind. No registry or engine: `RULES` is a tuple. |
| VI Documentation | Rule reference, check reference and field reference updated in the same pull request. |
| VII Dependency discipline | No new dependency. |
| IX Every rule names its source | `source` is a required field of `Rule`, so mypy refuses a rule without one. |
| X Rules, examples and code change together | One object per rule drives check, documentation and example test. `CHANGELOG.md` gains a **Scheme changes** entry. |
| XI Vocabulary from the published vocabularies | Concepts by URI, read through `Vocabularies`. No term in the code. |
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
├── rules.py            new: Rule, RequiredWhen, AllowedWhen, Domain, Condition, Example, RULES
├── check.py            Kind.RULE; PROBLEM_COLUMNS gains rule, related; holds(), rule_lines(); calls each rule
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

### `ghfdb.qc.rules`

The rules are declared in Python, so mypy and the linters check every rule as they check the rest
of the code. Nothing outside the package reads them, so they need no file format of their own
(D-4).

```python
@dataclass(frozen=True)
class Rule:
    identifier: str          # "CF-1", never changed or reused
    statement: str
    source: str              # a source key, as in the field schema
    reasoning: str
    example: Example

    def fields(self, schema) -> tuple[str, ...]: ...        # every field the rule relates
    def problems(self, check: "DatasetCheck") -> pandas.DataFrame: ...   # raises NotImplementedError
    def diagram(self, schema) -> str: ...                   # Mermaid flowchart text, raises NotImplementedError

@dataclass(frozen=True)
class RequiredWhen(Rule):
    domain: Domain           # the fields required are those mandatory for this domain only

@dataclass(frozen=True)
class AllowedWhen(Rule):
    when: Condition          # a field and the concepts that make the rule apply
    then: Condition          # a field and the concepts it may then hold
    alternatives: tuple[Condition, ...] = ()   # further conditions, any one of which also applies

RULES: tuple[Rule, ...] = (CF_1, CF_2, CF_3, CF_4)
```

- `Domain` and `Condition` are frozen dataclasses: a field code and a tuple of concept URIs.
  `BOREHOLE` and `PROBE_SENSING` are the two `Domain` constants, with their source and D-1.
- Concept URIs are module constants built from the scheme's identifier, so a misspelt concept name
  is a lint error and a concept the vocabularies withdraw fails the check. No term is written in
  the module (FR-005, Article XI).
- `Rule.problems(check)` returns lines in the problem table's shape, of kind `rule`. It receives the
  `DatasetCheck`, which holds the data, the schema and the terms of every concept (below), and
  offers the steps every rule shares:
  - `check.each_value(field, cells)`, which exists today, to split a cell holding several values.
  - `check.holds(condition)`: the rows where every value of the condition field is in its allowed
    values and at least one is a term of the condition. An empty cell, or one with a value not in
    the vocabulary, never holds, so a rule is never checked on a field that already has a problem
    (FR-004).
  - `check.rule_lines(rule, field, values, related)`: builds the lines, as `lines()` does for the
    field problems. `related` is the condition field's code, published column name and the value
    found.
- `RequiredWhen.problems()`: on the rows where the child's exploration method is in the domain, one
  line per required field that is empty.
- `AllowedWhen.problems()`: on the rows where `when` or any alternative holds, the `then` field split into its values.
  A value that is in the field's allowed values and is not a term of `then` is one line. A value
  not in the vocabulary already has its own problem and is skipped.
- A rule whose fields have no column in the workbook returns no lines, and the column problem
  stands.
- A rule that fits neither kind later is a new subclass with its own `problems()` and `diagram()`.
  Nothing else changes, because the check only calls those two methods.
- A *required when* rule with its fields listed, rather than read from a domain, is added with the
  first agreed rule that needs it, not now (Article III).
- `source` uses the field schema's source keys, so both cite sources the same way and the
  documentation resolves them with the same lookup (`field_reference.py`, `sources`). The lookup
  gains `fuchs-2023-table-4`. No rule cites a ruling of this feature, so no new decision key is needed.
- `Example` holds only the values of the fields the rule reads. A vocabulary value is a concept URI
  constant, resolved to its term like the rule's own concepts. Number and text values are plain.
  The expected problems give the field codes, and the expected `related` is derived from the
  resolved term. The test lays the values over the `valid_child` fixture (`tests/conftest.py`).

### `ghfdb.qc.check`

- `Kind.RULE = "rule"`. `PROBLEM_COLUMNS` gains `rule` and `related`, empty for the other kinds.
- `DatasetCheck(data, schema, rules=RULES)`: on construction, every concept URI the rules and
  examples name is turned into its term with `ghfdb.fields.schema.allowed_values(field,
  vocabularies)` for the field it is used in. A URI that is not an allowed value of that field (a
  collection, a concept of another scheme, or a concept no longer published) raises
  `MissingSchemeError` naming the rule and the URI (FR-011). The field schema already holds the
  allowed values, so this reads no file of its own.
- `problems()` builds the field problems, then joins `rule.problems(self)` for every rule, and
  sorts by row and then field order, rule lines after the field lines of the same row.

### `Dataset.check` and `ghfdb.cli`

- `Dataset.check(schema=None, rules=RULES)`. Its docstring, and `Report`'s, list the two new
  columns.
- `ghfdb check` applies `RULES`. A `MissingSchemeError` from a rule's concept gives status 2, as one
  from the field schema does now.

### `ghfdb.qc.report.Report`

- Each rule problem shows its identifier, linked to
  `https://ihfc-iugg.github.io/ghfdb/reference/rules.html#<id>`, the identifier lowercased, and its
  statement. The `related`
  value is shown beside the field's own value. Layout is settled by eye at the walkthrough; the
  tests assert the cells, never the wording.

### Documentation

- `docs/extensions/rule_reference.py` renders `docs/reference/rules.md` from `RULES` while the
  documentation builds: one entry per rule with its identifier as anchor, statement, fields related (linked to
  their field reference entries), source, reasoning, the Mermaid flowchart from the rule's `diagram()`, and the worked example as a table of values and the problem expected. A
  section before the entries explains the two kinds and the domain mapping, with D-1 cited.
- Node labels in the flowcharts are quoted, since field titles hold brackets and parentheses.
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

- `tests/test_qc/test_rules.py`: `RULES` resolve against the test vocabularies, and the domain
  rules read `C5`, `C31`, `C32` and `C6`, `C23` from the schema (expected sets written in the test,
  not derived). A concept that is not an allowed value of its field fails, naming the rule. One test
  resolves `RULES` against the vocabularies as currently published (`published_vocabularies`), so
  the suite fails when a concept is withdrawn (AS 2.6). Each kind on a small DataFrame: condition held and broken, condition not held, condition field empty,
  condition value not in the vocabulary, target value not in the vocabulary, a target field holding several values, a missing column.
  Also: a condition field holding several values, and one child breaking CF-1 with two empty
  fields and CF-3 at once, giving three rule lines after its field lines.
- `TestWorkedExamples` in `tests/test_qc/test_rules.py`: one parametrised test over `RULES`: each
  example over `valid_child` gives exactly the expected rule problem, and `valid_child` alone gives
  none. Every rule has an example because `Rule` requires one.
- `tests/test_qc/test_check.py`: the end-to-end test of a seeded workbook gains one child per rule.
  SC-004 is already shown by the test of a correctly filled template in `tests/test_cli.py`.
- The 90,000-child speed test (`tests/test_cli.py`, `TestSpeed`) applies the rules, and its
  `large_workbook` fixture seeds one child in a hundred breaking a rule (SC-006).
- `tests/test_docs/test_extensions/test_rule_reference.py`: every rule in `RULES` has an entry, no
  entry exists without a rule, every entry has a source, reasoning, diagram and example; the field
  reference lists each rule under every field it relates.
- No test asserts wording or layout. Problems are asserted as `(row, code, kind, rule)`.

## Complexity Tracking

None. Nothing in this plan departs from the constitution.
