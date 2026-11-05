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
