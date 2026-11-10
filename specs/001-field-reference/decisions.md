# Decisions: A field reference for the upload template

## Given by the maintainer

These were settled before the specification was written.

| # | Decision |
|---|---|
| G-1 | The machine-readable field description is one Frictionless Table Schema covering every upload template field. Per-column facts live in it: type, unit, obligation, range, allowed values and missing-value markers. Cross-field rules and scoring are not in it. |
| G-2 | Every field carries both its field code (`P1`–`P13`, `C1`–`C53`, the header row of the template) and its published column name (row 6 of the template, such as `q` or `lat_NS`). |
| G-3 | Allowed values of vocabulary fields are read from the IHFC Controlled Vocabularies as currently published at their permanent identifiers, and never typed by hand or copied into the field schema (`CONSTITUTION.md`, Article XI). Each such field links to the identifier of its concept scheme, and of its collection where there is one. The field schema states no release, version or DOI, because data assessors do not choose which version they use (maintainer, 2026-11-04). |
| G-4 | The field list comes from the current published upload template, sheet `data list`. A newer template version is an ordinary change to the field reference. |
| G-5 | Every rule names its source (`CONSTITUTION.md`, Article IX): Fuchs et al. (2023) Appendix A, the template, or a recorded decision. |
| G-6 | The field reference in the documentation follows `docs/contributing/standards/documentation.md` for reference pages, with simplified Mermaid diagrams where a process is described. |

## Self-resolved

Each of these filled a gap the issue left open. Each is the reading the specification is written
to.

### D-1 — The assessment fields A1–A8 are included

The current template has 74 fields: the 66 parent and child fields and eight assessment fields,
`A1`–`A8` (reviewer name, reviewer comment, review date, country, region, continent, domain,
unique entry ID). `CONTEXT.md` defines field codes as `P` and `C` only.

**Chosen:** all 74 are described, the assessment fields grouped separately, with the template as
their source. The template is what assessors fill in, and the generated template (#5) has to
reproduce every column. `CONTEXT.md` gains the assessment fields.

**ADR:** none — a reading of the sources or a local choice for this feature, which nothing else inherits

### D-2 — The misspelled published column names are recorded correctly and rejected

Row 6 of the template spells two names wrongly: `tc_pT_fuction` (C46) and `Ref_ISGN` (C49).

**Chosen:** the field schema records `tc_pT_function` and `Ref_IGSN` only. The GHFDB portal
uses the correct spellings and rejects the misspelled ones, and the vocabularies name
`tc_pT_function`. The misspelled forms are not earlier names, so the check does not accept them:
a workbook whose header carries one has an unknown column, and that problem suggests the
published column name it is closest to. The field then has no column, like any field a workbook
leaves out. `earlierColumnNames` holds only names an earlier version of the template really
published, such as `water_temperature` for C24.

**ADR:** none — a reading of the sources or a local choice for this feature, which nothing else inherits

### D-3 — Where the template and Appendix A disagree, the template is followed

**Chosen:** the field reference follows the current template and names it as the source, and each
disagreement found while building it is added to this file as a decision of its own. The template
is what assessors fill in today. Recording each disagreement keeps it open to review instead of
settling it silently.

**ADR:** none — a reading of the sources or a local choice for this feature, which nothing else inherits

### D-4 — An empty cell is the only missing value

**Chosen:** `[Unspecified]` and similar terms are allowed values. The field schema's missing-value
marker is the empty cell and nothing else. This follows the published vocabularies, which publish
`Unspecified` as a concept, and avoids repeating the old tool's confusion between an unspecified
value and missing data.

**ADR:** none — a reading of the sources or a local choice for this feature, which nothing else inherits

### D-5 — Fields with no published vocabulary

- **A fixed set the paper defines** (P9 heat production flag, C9 relevant child: yes, no or
  unspecified) is listed with its source in Appendix A. These are not vocabulary terms, so
  Article XI does not apply, but they are flagged as the first candidates if the vocabularies ever
  publish them.
- **Two external vocabularies** (C25 lithology, C26 stratigraphic age) are published by their
  owners, not by the IHFC. The template writes their terms as the last segment of the concept's
  URI. The allowed values are read from the file each owner publishes, as ADR 0007 records, and
  the entry links to that file and says that several values may be given, separated by
  semicolons. The old tool's copied lists for these fields had no source or version, and copying
  them again would be the same defect.

**ADR:** none — a reading of the sources or a local choice for this feature, which nothing else inherits

### D-6 — A field may draw on one collection of a concept scheme

The heat-flow corrections scheme serves nine fields (C11–C19) and groups its concepts into
collections such as in-situ conditions flags and environmental effect flags. **Chosen:** each
field links to its scheme, and where the vocabularies group concepts into a collection for that
field, to that collection, whose allowed values are then its members. Which collection serves
which field is read from the vocabularies where they say so, and recorded as a decision where
they do not.

**ADR:** none — a reading of the sources or a local choice for this feature, which nothing else inherits

### D-7 — Example values in the template's range row are not rules

For vocabulary fields the template's "Allowed range of values" row often holds one example term,
such as `[Onshore (continental)]` for P7. **Chosen:** these are ignored as rules. The allowed
values come from the published vocabulary.

**ADR:** none — a reading of the sources or a local choice for this feature, which nothing else inherits

### D-8 — The field schema ships with the package and the vocabulary files are downloaded when needed

**Chosen:** the field schema is part of the installed package. The vocabulary files are not: the
package downloads each scheme's Turtle file from its identifier with `.ttl` added the first time it
is needed, through a `requests-cache` session that keeps it in a cache directory outside the
repository. The server's `ETag`, `Last-Modified` and `Cache-Control` decide whether the cached file
is still current, so an unchanged file costs a `304` and there is no fixed expiry that could hide a
change. The cached file stays in use when the server cannot be reached. Deleting the cache directory refreshes everything.

**ADR:** docs/adr/0003-vocabularies-are-read-from-their-permanent-identifiers.md

### D-9 — A change in the vocabularies needs no change to the field schema

**Chosen:** the allowed values are read from the published files, so nothing is regenerated and
nothing can be edited by hand. The repository's checks start every run with an empty cache, so they
read the files as currently published and fail when the vocabularies change beneath the field
schema. A scheme or collection that is no longer defined where it is published stops the load,
naming the field.

**ADR:** docs/adr/0003-vocabularies-are-read-from-their-permanent-identifiers.md

### D-10 — Three stories

The data assessor's lookup and the developer's loading are separate stories, because they are
different people. Learning that the vocabularies changed is a third, because a maintainer deals
with it on its own. Everything else is a scenario under one of them.

**ADR:** none — a reading of the sources or a local choice for this feature, which nothing else inherits

### D-11 — No sketch

The feature adds documentation reference pages laid out by the documentation standard, and no
screen. It is not sketched first.

## Made while planning

Each disagreement between the template and Fuchs et al. (2023) Appendix A is settled for the
template (D-3) and recorded here, so a reader can see what the paper says instead. The full
comparison is in `research.md`.

**ADR:** none — a reading of the sources or a local choice for this feature, which nothing else inherits

### D-12 — Field names follow the template, with one misspelling corrected

Nine names differ from Appendix A's (P4, P5, P10, P11, C8, C20, C35, C36, C47). **Chosen:** the
template's names. C37 is written "Number of temeprature recordings" in the template. **Chosen:**
"Number of temperature recordings", as for the column names in D-2, sourced to this decision.

**ADR:** none — a reading of the sources or a local choice for this feature, which nothing else inherits

### D-13 — Units follow the template, and a date format is not a unit

Units differ for P11 (`m` against `-`), C23 (`degree` against `deg`), C33 and C34 (`hr` against
`hours`). **Chosen:** the template's. C38's unit row holds `YYYY-MM`, which is the format of the
value. **Chosen:** C38 has no unit, and `YYYY-MM` is recorded as its format, sourced to the
template.

**ADR:** none — a reading of the sources or a local choice for this feature, which nothing else inherits

### D-14 — Obligation follows the template, and the assessment fields have none

C2 and C37 are recommended in the template and mandatory in Appendix A. **Chosen:** recommended.
C46 is mandatory in the template. **Chosen:** mandatory.
The assessment fields are `-` in the template and `A` in Appendix A. **Chosen:** no obligation.
They are filled in by the data assessment team, not by a contributor, and the field reference says
so.

**ADR:** none — a reading of the sources or a local choice for this feature, which nothing else inherits

### D-15 — Domain follows the template

P12, P13 and C20 are `B,S` in the template, `B` and `S` in Appendix A. **Chosen:** `B,S`. C4,
C29 and C30 are `B` in the template. **Chosen:** `B`.

**ADR:** none — a reading of the sources or a local choice for this feature, which nothing else inherits

### D-16 — Quality relevance is written in this repository's terms

The template writes `U score`, `M score` and `P Score`. **Chosen:** `U-score`, `M-score` and
`perturbation flags`, the terms of `CONTEXT.md`, which avoids "P-score". P6 is `M score` in the
template and `M score (probe sensing)` in Appendix A, and C46 is `M score` in the template and
`-` in Appendix A. **Chosen:** the template's, for both.

**ADR:** none — a reading of the sources or a local choice for this feature, which nothing else inherits

### D-17 — Ranges follow the template

C4, C5 and C6 run to one decimal place in the template and two in Appendix A. C23 runs to `99.9`
in the template and `90` in Appendix A. **Chosen:** the template's. C27–C30 are written
`– 99,999.99 – 99,999.99` in the template. **Chosen:** the leading dash is the minus sign, so the
range is −99,999.99 to 99,999.99, as Appendix A writes it.

Version 2026.03 of the template gives some fields two ranges, one in row 8 of the `data list`
sheet and one in row 2 of the `controlled vocabulary` sheet. C24 is −9.99 to 999.99 on the first
and −273.15 to 999.99 on the second, and C50–C53 are ±99,999.99 on the first and −999.99 to
9,999.99 on the second. **Chosen:** where the two sheets disagree, the `data list` row 8 value,
because that is the row the template describes the column with. C24 keeps −9.99 to 999.99 and
C50–C53 take −99,999.99 to 99,999.99.

**ADR:** none — a reading of the sources or a local choice for this feature, which nothing else inherits

### D-18 — Types come from Appendix A, written as Table Schema types

The template states no type. **Chosen:** Appendix A's, each mapped once: a float to `number` with
its decimal places, an integer to `integer`, `Char (255)` to `string` of at most 255 characters, a
`POSIX date (YYYY-MM)` to a `string` in that format, and the bit and boolean fields (P9, C9) to a
`string` from their fixed list (D-5). C38 also accepts `[Unspecified]`, as Appendix A's range
says.

**ADR:** none — a reading of the sources or a local choice for this feature, which nothing else inherits

### D-19 — Meanings of the assessment fields

Appendix A gives no meaning for A1–A8. **Chosen:** each is given a one-line meaning taken from its
name, sourced to this decision, until the data assessment team writes better ones: the reviewer's
name, the reviewer's comment, the date of the review, the country, region and continent of the
site, the domain recorded in review, and the child's unique ID.

**ADR:** none — a reading of the sources or a local choice for this feature, which nothing else inherits

### D-20 — How a term is written in a cell is a property of the field

The template writes the temperature methods (C31, C32) by notation (`[LOGeq]`) and every other
vocabulary field by label (`[Bullard method]`), although `conductivity-saturation` publishes
notations too. **Chosen:** each vocabulary field records which form its terms take, sourced to the
template. A concept with no notation (`Other`, `Unspecified` in the temperature methods) is
written by its label. The label is the vocabularies' English preferred label. The template's older
labels, which v2026.1 keeps as alternative labels, are not allowed values.

**ADR:** none — a reading of the sources or a local choice for this feature, which nothing else inherits

### D-21 — Allowed values are listed in the order of their terms

A concept scheme has no order of its own. **Chosen:** allowed values are sorted by term, ignoring
case, so the list is identical whenever the vocabularies are. The members of a `skos:OrderedCollection`
are the exception: they keep the collection's order, because the vocabularies gave them one.

**ADR:** none — a reading of the sources or a local choice for this feature, which nothing else inherits

### D-22 — Example values and formats in Appendix A are guidance, not rules

C20 lists `[R/V Ship]`, `[D/V Platform]`, `[D/V Glomar Challenger]`,
`[D/V JOIDES Resolution]` and `[Expedition-Cruise number]` as examples, which no vocabulary
publishes, and C7 and C8 show a reference format (`[First author_Year_Title_Journal/ Publisher_doi]`).
**Chosen:** these fields take free text, and the examples are recorded as guidance, sourced to
the template for C20 and to Appendix A for C7 and C8.

**ADR:** none — a reading of the sources or a local choice for this feature, which nothing else inherits

### D-23 — Fields that hold several values

Lithology and stratigraphic age (C25, C26) take several values separated by semicolons (D-5), and
Appendix A says the same of the IGSNs in C49. **Chosen:** these three fields record the semicolon
as their separator. C25 and C26 are the only vocabulary fields that take several values: the
template writes their terms separated by semicolons, and says so of no other vocabulary field.

## Made at the design review

**ADR:** none — a reading of the sources or a local choice for this feature, which nothing else inherits

### D-24 — Vocabulary bindings are the permanent identifiers

**Chosen:** a vocabulary field links to the permanent identifier of its scheme (such as
`https://w3id.org/ihfc-iugg/vocabularies/conductivity-methods`) and of its collection (such as
`https://w3id.org/ihfc-iugg/vocabularies/heat-flow-corrections/insitu`), written by hand. The
identifiers are permanent by promise, so a hand-written one does not go stale, and the scheme's
file is at the identifier with `.ttl` added.

**ADR:** docs/adr/0003-vocabularies-are-read-from-their-permanent-identifiers.md

### D-25 — The value format is not called `format`

`format` is a reserved Table Schema property, and a `YYYY-MM` there makes the schema invalid.
**Chosen:** C38 and A3 record it as `valueFormat`, checked by `constraints.pattern`.

**ADR:** none — a reading of the sources or a local choice for this feature, which nothing else inherits

### D-26 — The explanation stays on the field reference, and the developer gets a guide

FR-014 puts the explanation of where facts come from, and of how the allowed values stay current, on the field
reference. **Chosen:** it stays there, as the specification says, and the developer's task of
loading the field definitions gets a short guide page of its own, as the documentation standard
asks of every feature.

**ADR:** none — a reading of the sources or a local choice for this feature, which nothing else inherits

### D-27 — Reading the vocabularies ships in the package

**Chosen:** `ghfdb.fields.vocabularies` is part of the package and `rdflib` is a runtime
dependency, because loading the field schema reads the vocabularies. Keeping the reading outside
the package would leave it untyped and uncovered by the checks every other module passes.

**ADR:** none — a reading of the sources or a local choice for this feature, which nothing else inherits

## Made at the code review

### D-28 — The date of acquisition accepts a range of months

Appendix A's meaning for C38 asks for a range of months, written `YYYY-MM; YYYY-MM`, when the
data were acquired over more than one month, and the template's unit row gives only `YYYY-MM`.
**Chosen:** C38 accepts one month, a range written as Appendix A writes it, or `[unspecified]`.
Its format is sourced to this decision.

**ADR:** none — a reading of the sources for one field
