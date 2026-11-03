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

## Made while planning

Each disagreement between the template and Fuchs et al. (2023) Appendix A is settled for the
template (D-3) and recorded here, so a reader can see what the paper says instead. The full
comparison is in `research.md`.

### D-12 — Field names follow the template, with one misspelling corrected

Nine names differ from Appendix A's (P4, P5, P10, P11, C8, C20, C35, C36, C47). **Chosen:** the
template's names. C37 is written "Number of temeprature recordings" in the template. **Chosen:**
"Number of temperature recordings", as for the column names in D-2, sourced to this decision.

### D-13 — Units follow the template, and a date format is not a unit

Units differ for P11 (`m` against `-`), C23 (`degree` against `deg`), C33 and C34 (`hr` against
`hours`). **Chosen:** the template's. C38's unit row holds `YYYY-MM`, which is the format of the
value. **Chosen:** C38 has no unit, and `YYYY-MM` is recorded as its format, sourced to the
template.

### D-14 — Obligation follows the template, and the assessment fields have none

C2 and C37 are recommended in the template and mandatory in Appendix A. **Chosen:** recommended.
The assessment fields are `-` in the template and `A` in Appendix A. **Chosen:** no obligation.
They are filled in by the data assessment team, not by a contributor, and the field reference says
so.

### D-15 — Domain follows the template

P12 and C20 are `B,S` in the template, `B` and `S` in Appendix A. **Chosen:** `B,S`.

### D-16 — Quality relevance is written in this repository's terms

The template writes `U score`, `M score` and `P Score`. **Chosen:** `U-score`, `M-score` and
`perturbation flags`, the terms of `CONTEXT.md`, which avoids "P-score". P6 is `M score` in the
template and `M score (probe sensing)` in Appendix A, and C46 is `M score` in the template and
`-` in Appendix A. **Chosen:** the template's, for both.

### D-17 — Ranges follow the template

C4, C5 and C6 run to one decimal place in the template and two in Appendix A. C23 runs to `99.9`
in the template and `90` in Appendix A. **Chosen:** the template's. C27–C30 are written
`– 99,999.99 – 99,999.99` in the template. **Chosen:** the leading dash is the minus sign, so the
range is −99,999.99 to 99,999.99, as Appendix A writes it.

### D-18 — Types come from Appendix A, written as Table Schema types

The template states no type. **Chosen:** Appendix A's, each mapped once: a float to `number` with
its decimal places, an integer to `integer`, `Char (255)` to `string` of at most 255 characters, a
`POSIX date (YYYY-MM)` to a `string` in that format, and the bit and boolean fields (P9, C9) to a
`string` from their fixed list (D-5). C38 also accepts `[Unspecified]`, as Appendix A's range
says.

### D-19 — Meanings of the assessment fields

Appendix A gives no meaning for A1–A8. **Chosen:** each is given a one-line meaning taken from its
name, sourced to this decision, until the data assessment team writes better ones: the reviewer's
name, the reviewer's comment, the date of the review, the country, region and continent of the
site, the domain recorded in review, and the child's unique ID.

### D-20 — How a term is written in a cell is a property of the field

The template writes the temperature methods (C31, C32) by notation (`[LOGeq]`) and every other
vocabulary field by label (`[Bullard method]`), although `conductivity-saturation` publishes
notations too. **Chosen:** each vocabulary field records which form its terms take, sourced to the
template. A concept with no notation (`Other`, `Unspecified` in the temperature methods) is
written by its label. The label is the release's English preferred label. The template's older
labels, which v2026.1 keeps as alternative labels, are not allowed values.

### D-21 — Allowed values are listed in the order of their terms

A concept scheme has no order of its own. **Chosen:** allowed values are sorted by term, ignoring
case, so a regenerated list is identical when the release is.

### D-22 — Example values and formats in Appendix A are guidance, not rules

C20 lists `[Expedition cruise number]`, `[R/V Ship]` and similar, which no vocabulary publishes,
and C7 and C8 show a reference format (`[First author_Year_Title_Journal/ Publisher_doi]`).
**Chosen:** these fields take free text, and the examples are recorded as guidance, sourced to
Appendix A.

### D-23 — Fields that hold several values

Lithology and stratigraphic age (C25, C26) take several values separated by semicolons (D-5), and
Appendix A says the same of the IGSNs in C49. **Chosen:** these three fields record the semicolon
as their separator. No vocabulary field is recorded as taking several values: neither the template
nor Appendix A says one does.

## Made at the design review

### D-24 — Vocabulary bindings are written by scheme name

**Chosen:** a vocabulary field names its scheme and collection by the last segment of their URI
(`conductivity-methods`, `insitu`), and the step that adopts a release writes the full URIs with
the allowed values. The vocabularies' main branch has already moved its URIs to `w3id.org`, so a
binding written as a full URI would need a hand edit at the first move, which FR-015 rules out.

### D-25 — The value format is not called `format`

`format` is a reserved Table Schema property, and a `YYYY-MM` there makes the schema invalid.
**Chosen:** C38 and A3 record it as `valueFormat`, checked by `constraints.pattern`.

### D-26 — The explanation stays on the field reference, and the developer gets a guide

FR-014 puts the explanation of where facts come from, and of adopting a release, on the field
reference. **Chosen:** it stays there, as the specification says, and the developer's task of
loading the field definitions gets a short guide page of its own, as the documentation standard
asks of every feature.

### D-27 — The release step ships in the package

**Chosen:** `ghfdb.fields.release` is part of the package, behind the optional `vocabularies`
extra, and the Python API page introduces it as maintainer tooling. Keeping it outside the package
would leave it untyped and uncovered by the checks every other module passes.
