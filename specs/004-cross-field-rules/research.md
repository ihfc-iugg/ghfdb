# Research: Check the rules that relate several fields

**Input**: `spec.md`, `decisions.md`, the old checking tool's `schemas/conditional_rules.yaml`
(at commit `dfe6664` of its current fork), Fuchs et al. (2023) and the IHFC Controlled
Vocabularies as published today. There is no `planning-notes.md` and no sketch.

## The old tool's rules, traced to their sources

The old tool applies 20 rules in five groups. None names a source. Each group was read against
Fuchs et al. (2023): section 4.2, Table 4, and the field descriptions of Appendix A.

| Group | Old rules | Source found | Outcome |
|---|---|---|---|
| Fields mandatory in one domain: interval bottom (`C5`) and temperature methods (`C31`, `C32`) for borehole and mine data, penetration depth (`C6`) and probe tilt (`C23`) for probe-sensing data | 4 (`borehole_requires_c4_c5`, `borehole_requires_c31_c32`, `probing_requires_c6`, `probing_requires_c23`) | Table 4 and Appendix A give each field's obligation and domain. The field schema records both, citing the upload template, which agrees with Table 4 for these five fields | **Checked**, as CF-1 and CF-2. `C4` is mandatory in both domains, so the field check already reports it |
| An indirect exploration method limits the temperature methods (`C31`, `C32`) | 2 | None. The paper's exploration methods do not include indirect methods, which the vocabularies added later | **Raised as an issue** |
| A probing method allows only `[Unspecified]` as temperature method | 6 | None. Appendix A gives the temperature methods the borehole domain only, which makes them not applicable to probing. It does not say they must hold `[Unspecified]` rather than be empty | **Raised as an issue** |
| The in-situ flag (`C11`) limits the pT conditions (`C45`) | 5 | None stated. The two fields' descriptions are consistent with the old rules, but neither says the other limits it | **Raised as an issue** |
| The pT conditions (`C45`) limit the pT function (`C46`) | 3 | None stated. As above | **Raised as an issue** |

Reading Appendix A for the rules above found one more, which the old tool did not apply:

| Rule | Source | Outcome |
|---|---|---|
| Thermal conductivity location (`C42`) may be `[Literature or unspecified]` only if the thermal conductivity source (`C41`) is `[Assumed from literature]` | Appendix A, field `C42`, "Value description" column | **Checked**, as CF-3 |

Two more statements in the paper are relevant, and each is unclear:

- `C35` and `C36` (temperature correction methods) are "applicable only if gradient correction for
  borehole effects is reported". No field records that, so the condition cannot be read from a
  workbook. **Raised as an issue.**
- Section 4.2.3 says the thermal conductivity method (`C43`) "is only mandatory for the
  probe-sensing evaluation scheme", while Table 4 makes it mandatory in both domains. The field
  check follows Table 4 today. **Raised as an issue**, because which one holds changes what is
  reported as missing.

Every old rule is therefore either checked or raised (SC-003). Seven issues are filed during the
build: one per row marked "raised" (six), and one asking the team to confirm the domain of each
exploration method (D-1), which says that until then an indirect method is checked as borehole
data. Each states the old rule, what the paper says and the question
the data assessment team has to settle.

## The domain of a child

The paper's domains are "boreholes and mines on the continents" (`B`) and "shallow probe-sensing"
data (`S`), and its exploration methods are drilling, mining, tunnelling, the two probing methods,
other and unspecified. Drilling, mining and tunnelling read as `B`, the probing methods as `S`.

The vocabularies have three concepts the paper does not: `drilling-clustering`,
`probing-clustering` and `indirect`. The clustered methods are their base method standing for a
cluster of sites (`skos:definition` of each), so they take its domain. Indirect methods follow the
old tool and D-1. The ruling is recorded in `decisions.md` and raised with the issues so the data
assessment team can confirm it. `other` and `unspecified` belong to no domain.

The assessment field `A7` records a domain, but the data assessment team fills it in during review,
after the check is run. It cannot be what the check reads.

The mapping refers to the concepts of `https://w3id.org/ihfc-iugg/vocabularies/exploration-methods`
by URI. The vocabularies have no collection for the two domains. Adding one would be the better
home for the mapping, but it is a change to the vocabularies themselves and waits on the same
confirmation.

## Where the rules are kept

The rules are declared in Python, in `ghfdb.qc.rules`, as instances of frozen dataclasses. The field
schema is a JSON file because it is a Frictionless Table Schema, a published format that other tools
read (ADR 0004). Cross-field rules have no such format, and nothing outside the package reads them.
In Python, mypy and the linters check every rule, a misspelt concept or a missing source is caught
before a test runs, and a rule that fits no existing kind can carry its own check. The check, the
documentation build and the tests all import `RULES`, so they still cannot disagree (FR-008,
FR-009, FR-013, Article X).

Rules are not added to the field schema file. A Table Schema has no place for a rule across fields.

If citable scheme releases (R8) need a machine-readable copy of the rules, it is generated from
`RULES` then.

## Two kinds of rule

Every rule this feature checks, and every rule raised for the team, is one of two shapes. Each is a
subclass of `Rule` implementing `problems()`. A rule that fits neither is a new subclass:

| Kind | Reads | Problem when |
|---|---|---|
| **required when** | when a field holds one of a set of concepts, other fields must be filled | the condition holds and a required field is empty |
| **allowed when** | when a field holds one of a set of concepts, another field may hold only some concepts | the condition holds and the other field holds a value outside its allowed set |

CF-1 and CF-2 are *required when*: the condition is the exploration method being in the domain,
and the required fields are those the field schema marks mandatory for that domain only. They are
not listed in the rule by hand. The rule names the domain and its exploration methods,
and the required fields are read from the field schema, so a change of obligation in the field
schema changes the rule with it.

CF-3 is *allowed when*, with the condition on `C42` and the allowed set on `C41`.

The rules the team may agree later fit the same two kinds, so no third kind is built now.

## Referring to concepts

A rule names concepts by URI constants, and the URIs are turned into terms when the check starts,
through the allowed values the field schema already holds. That keeps the terms out of the code
(Article XI, FR-005), and a workbook term is matched exactly as the field check
matches it. A concept URI that the published scheme no longer defines fails the check, naming the
rule and the URI. That is what makes the repository's checks fail when the vocabularies change
under a rule, as they already do for a field (FS-001, FR-017).

## Reporting a rule problem

The problem table today has the columns `row`, `code`, `column_name`, `kind`, `value` and
`suggestion`. A rule problem is one more line in it, of kind `rule`:

- `code`, `column_name` and `value` are the field the rule asks the assessor to fill or change:
  the empty required field, or the field holding the value outside the allowed set. A field holding
  several values gets one line per value outside the set.
- Two new columns, `rule` (the identifier) and `related` (the condition field's code, published
  column name and value, for example `P12 explo_method [Drilling]`), are empty for the other kinds.

This keeps one line per mistake, so the counts the command prints still count mistakes. It names
every field the rule relates and the value found in each (FR-002). New columns are additive to
the Python API and the report layout (Article XIV).

The report shows the rule's statement beside the identifier and links the identifier to its entry
in the published documentation, `https://ihfc-iugg.github.io/ghfdb/reference/rules.html#cf-1`, the identifier lowercased as Sphinx
writes anchors. The link goes to the latest published reference, and `check.md` says so.
The report needs no network to open or read, so it still works offline. Only following the link
needs one.

## Not checking a rule twice

The rule check runs after the field check, on the same `Dataset`, and receives the cells that
already have a field problem. A rule is skipped on a child when its condition field is empty or
has a field problem. For *allowed when*, a target value that is not in the vocabulary is skipped.
It already has its own problem (FR-004).

## Performance

Each rule is a few boolean masks over whole columns: `isin` for the condition, `isin` or a blank
test for the target, and an `explode` for a field holding several values, exactly as the field
check does. At 90,000 children that is milliseconds per rule, far inside SC-006's 15 seconds. The
existing speed test (`tests/test_cli.py`, `TestSpeed`, on the session-scoped `large_workbook`
fixture) applies the rules once the command does, and its fixture seeds one child in a hundred
breaking a rule.

## The documentation

`docs/reference/rules.md` is rendered from `RULES` by a Sphinx extension beside the field
reference extension (`docs/extensions/rule_reference.py`). It holds one entry per rule, in the same
order and with the same facts for each, and a Mermaid flowchart of its logic from the rule's
`diagram()` method. Each kind draws its own, so a new kind brings its diagram with it. The field reference gains a line per
field naming the rules that involve it (FR-010). The check reference page (`docs/reference/check.md`)
describes the rule problem and its two columns.

## What already exists

| Piece | Where the search stopped |
|---|---|
| Rule definitions read by both the check and the documentation | **the language**: a Python module and dataclasses, imported by the check, `docs/extensions/rule_reference.py` and the tests |
| Turning concept URIs into terms | **this repo**: `ghfdb.fields.schema.allowed_values(field, vocabularies)`, which gives each allowed value of the rule's field with its URI. `Vocabularies.allowed_value` alone would also accept a collection URI, so it is not used directly |
| Splitting a field holding several values | **this repo**: `DatasetCheck.each_value` |
| Checking each rule's shape | **the type checker**: the rules are typed dataclasses, so mypy refuses a rule with a field missing |
| Cross-field checks on a DataFrame | **a maintained package was looked at**: pandera's wide checks return failing rows, but not the skip rule, the related values or the problem table's shape, so wrapping it would add a layer rather than replace code. **New code**: about a hundred lines, `ghfdb/qc/rules.py` with the two kinds' `problems()`, and `DatasetCheck.holds()` and `rule_lines()` |
| Mermaid diagrams in the documentation | **an installed package**: `sphinxcontrib-mermaid`, already used by the field reference. **New code**: generating a flowchart's text from a rule, a few lines in the rule reference template, with node labels quoted |
| A child to lay a worked example over | **this repo**: the `valid_child` fixture in `tests/conftest.py` |
| Rendering documentation pages from data | **this repo**: the Jinja templates in `docs/extensions/templates` |
