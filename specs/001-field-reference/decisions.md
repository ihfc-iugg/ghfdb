# Decisions: A field reference for the upload template

## Given by the maintainer

These were settled before the specification was written.

| # | Decision |
|---|---|
| G-1 | The machine-readable field description is one Frictionless Table Schema covering every upload template field. Per-column facts live in it: type, unit, obligation, range, allowed values and missing-value markers. Cross-field rules and scoring are not in it. |
| G-2 | Every field carries both its field code (`P1`–`P13`, `C1`–`C49`, the header row of the template) and its published column name (row 6 of the template, such as `q` or `lat_NS`). |
| G-3 | Allowed values of vocabulary fields are generated from a stated release of the IHFC Controlled Vocabularies, v2026.1 (DOI [10.5880/fidgeo.2026.065](https://doi.org/10.5880/fidgeo.2026.065)), and never typed by hand (`CONSTITUTION.md`, Article XI). Each such field records its concept scheme's URI. Moving to a newer release is a separate, explicit step. |
| G-4 | The field list comes from the current published upload template, sheet `data list`. A newer template version is an ordinary change to the field reference. |
| G-5 | Every rule names its source (`CONSTITUTION.md`, Article IX): Fuchs et al. (2023) Appendix A, the template, or a recorded decision. |
| G-6 | The field reference in the documentation follows `docs/contributing/standards/documentation.md` for reference pages, with simplified Mermaid diagrams where a process is described. |

## Self-resolved

Each of these filled a gap the issue left open. Each is the reading the specification is written
to.

### D-1 — The assessment fields A1–A8 are included

The current template has 70 fields: the 62 parent and child fields and eight assessment fields,
`A1`–`A8` (reviewer name, reviewer comment, review date, country, region, continent, domain,
unique entry ID). `CONTEXT.md` defines field codes as `P` and `C` only.

**Chosen:** all 70 are described, the assessment fields grouped separately, with the template as
their source. The template is what assessors fill in, and the generated template (#5) has to
reproduce every column. `CONTEXT.md` gains the assessment fields.

### D-2 — The misspelled published column names are recorded correctly

Row 6 of the template spells two names wrongly: `tc_pT_fuction` (C46) and `Ref_ISGN` (C49).

**Chosen:** the field schema records `tc_pT_function` and `Ref_IGSN`, and keeps the misspelled
form as the template's earlier spelling. The GHFDB portal uses the correct spellings and rejects
the misspelled ones, and the v2026.1 vocabulary release names `tc_pT_function`. Recording the
earlier spelling lets a later check recognise an outdated template and say so.

### D-3 — Where the template and Appendix A disagree, the template is followed

**Chosen:** the field reference follows the current template and names it as the source, and each
disagreement found while building it is added to this file as a decision of its own. The template
is what assessors fill in today. Recording each disagreement keeps it open to review instead of
settling it silently.

### D-4 — An empty cell is the only missing value

**Chosen:** `[Unspecified]` and similar terms are allowed values. The field schema's missing-value
marker is the empty cell and nothing else. This follows the published vocabularies, which publish
`Unspecified` as a concept, and avoids repeating the old tool's confusion between an unspecified
value and missing data.

### D-5 — Fields with no published vocabulary

- **A fixed set the paper defines** (P9 heat production flag, C9 relevant child: yes, no or
  unspecified) is listed with its source in Appendix A. These are not vocabulary terms, so
  Article XI does not apply, but they are flagged as the first candidates if the vocabularies ever
  publish them.
- **An open set** (C25 lithology, C26 stratigraphic age) has no list of allowed values. Its entry
  names the classification the paper recommends as guidance and says that several values may be
  given, separated by semicolons. The old tool's copied lists for these fields had no source or
  version, and copying them again would be the same defect.

### D-6 — A field may draw on one collection of a concept scheme

The heat-flow corrections scheme serves nine fields (C11–C19) and groups its concepts into
collections such as in-situ conditions flags and environmental effect flags. **Chosen:** each
field names its scheme, and where the release groups concepts into a collection for that field,
its allowed values are that collection. Which collection serves which field is read from the
release where it says so, and recorded as a decision where it does not.

### D-7 — Example values in the template's range row are not rules

For vocabulary fields the template's "Allowed range of values" row often holds one example term,
such as `[Onshore (continental)]` for P7. **Chosen:** these are ignored as rules. The allowed
values come from the vocabulary release.

### D-8 — The definitions ship with the package

**Chosen:** the field schema and the vocabulary terms it was generated from are part of the
installed package, so loading them needs no network access. The package is an offline tool for
assessors.

### D-9 — Moving to a newer vocabulary release is a maintainer's step with a report

**Chosen:** the maintainer names the release, the allowed values are regenerated, and the step
reports per field the concepts added, removed and relabelled. A release that lacks a scheme a
field names stops the move with nothing changed. The repository's checks fail when the allowed
values no longer match the stated release, which is what stops a hand edit.

### D-10 — Three stories

The data assessor's lookup and the developer's loading are separate stories, because they are
different people. Moving to a newer release is a third, because a maintainer sets out to do it on
its own. Everything else is a scenario under one of them.

### D-11 — No sketch

The feature adds documentation reference pages laid out by the documentation standard, and no
screen. It is not sketched first.
