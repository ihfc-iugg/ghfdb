# Decisions: Check the rules that relate several fields

Rulings made while specifying FS-004, with the reasoning too long to keep in `spec.md`.

### D-1 — A child's domain is read from its exploration method

The field schema records each field's domain, `B` for borehole and mine data and `S` for
probe-sensing data, but no field records which domain a child belongs to. The exploration method
(`P12`) is the only field that says how the data was gathered, so the domain is read from it.

| Exploration method | Domain |
|---|---|
| Probing (onshore lake, river and similar), Probing (offshore ocean), Probing with clustering | Probe-sensing (`S`) |
| Drilling, Drilling with clustering, Mining, Tunnelling | Borehole and mine (`B`) |
| Indirect (GTM, BSR, CPD and similar) | Borehole and mine (`B`) |
| Anything else, empty or not in the vocabulary | None: no domain rule is checked |

Counting indirect methods as borehole data follows the old checking tool. Indirect methods are
not gathered in a borehole. They are grouped with borehole data because the borehole fields, such
as the temperature methods, are the ones that describe them. This mapping is to be confirmed by
the data assessment team with the other rules, and is recorded here so it can be.

### D-2 — An empty field that is mandatory in one domain only is a rule problem

`CONTEXT.md` defines **missing** as a mandatory field left empty. A field mandatory in one domain
only, such as the interval bottom (`C5`) for borehole data, is mandatory only once the exploration
method is known. Reporting it as missing would hide the reason, and an assessor who reads "missing"
on a probe-sensing child would not see why. As a rule problem it names both fields: the exploration
method that makes the field mandatory, and the field left empty.

The workbook check (FS-003) already reports only fields mandatory in every domain as missing, so
nothing it reports changes.

### D-3 — The old checking tool's rules are a starting point, not a source

The old checking tool's rules (`schemas/conditional_rules.yaml`) name no source, and its other
schemas were found to disagree with the published vocabularies and with the 2023 paper. They are
therefore treated as a list of rules to trace, not as rules to copy. Each one enters this package
only with a source in Fuchs et al. (2023) or a recorded ruling. Each one that cannot be traced is
raised as an issue in this repository, so none is dropped without a record (SC-003).

The questions raised for the data assessment team:

| Issue | Question |
|---|---|
| [#30](https://github.com/ihfc-iugg/ghfdb/issues/30) | Which temperature methods are allowed for an indirect exploration method? |
| [#31](https://github.com/ihfc-iugg/ghfdb/issues/31) | Should probe-sensing data leave the temperature methods empty or give them as unspecified? |
| [#32](https://github.com/ihfc-iugg/ghfdb/issues/32) | Does the in-situ flag limit the thermal conductivity pT conditions? |
| [#33](https://github.com/ihfc-iugg/ghfdb/issues/33) | Do the pT conditions limit the thermal conductivity pT function? |
| [#34](https://github.com/ihfc-iugg/ghfdb/issues/34) | When do the temperature correction methods apply? |
| [#35](https://github.com/ihfc-iugg/ghfdb/issues/35) | Is the thermal conductivity method mandatory for borehole data? |
| [#36](https://github.com/ihfc-iugg/ghfdb/issues/36) | Confirm the domain of each exploration method (D-1) |

### D-4 — The rules are declared in Python, as dataclasses with a `problems()` method

The rules live in `ghfdb.qc.rules`: a frozen `Rule` dataclass and two subclasses, `RequiredWhen` and
`AllowedWhen`, each implementing `problems()` and `diagram()`. `RULES` is a tuple of the rules. The
check, the rule reference and the example tests all import it, so the three cannot disagree
(Article X).

The field schema is JSON because it is a Frictionless Table Schema, a published format other tools
read (ADR 0004). The rules have no such format and no reader outside the package, so a JSON file
would give up type and lint checking for nothing. In Python, mypy refuses a rule without a source
or an example, and a misspelt concept constant is a lint error.

A method per kind replaces a branch on the rule's kind inside the check. A rule that fits neither
kind is a new subclass with its own `problems()` and `diagram()`, and the check does not change.
Both subclasses are used now, so the base class is not built ahead of need (Article III).

If citable scheme releases (R8) need a machine-readable copy of the rules, it is generated from
`RULES`.

### D-5 — A rule problem is one line of the problem table, with two new columns

A rule problem names the field to fill or change in `code`, `column_name` and `value`, as every
other problem does. The new `rule` column gives the rule's identifier, and `related` gives the
condition field and its value. One line per mistake keeps the command's counts honest. The columns
are added, never renamed, so code reading the table keeps working (Article XIV).

### D-6 — The domain rules read their fields from the field schema

CF-1 and CF-2 do not list their fields. They take every field the field schema marks mandatory for
their domain only, so the obligation and domain stay recorded in one place, with their source, and
a change to either changes the rule.

### D-7 — The design review's findings, all applied to the plan

The design review approved the plan with no critical or high finding. Every medium and low finding
was applied as a plan edit rather than carried: `related` names the condition field's column name;
concepts resolve through `allowed_values` for the rule's field, so a collection URI cannot pass;
worked examples give concepts by URI; no list form of *required when* until a rule needs it; the
example tests sit in `test_rules.py` over `valid_child`; a rule reads which fields already have a problem from
the cells, rather than from a record of the field problems. D-1's reliance on
the old tool is raised with the team (T001), and the mapping is not changed before they rule.

### D-8 — `DatasetCheck` applies no rules unless it is given them

`DatasetCheck(data, schema, rules=(), vocabularies=None)` checks fields only when no rules are
passed. `Dataset.check` and the `ghfdb check` command pass `RULES` and the vocabularies the schema
was loaded with. The class stays a check of whatever it is given, which is what its own tests and
the field-check tests written before this feature construct, and the packaged rules are chosen
where the package's defaults are chosen already. The plan had `RULES` as the class default.
**ADR:** none — local to this feature, nothing downstream inherits it.
