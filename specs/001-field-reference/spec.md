# Feature Specification: A field reference for the upload template

**Feature Branch**: `001-field-reference`

**Created**: 2026-11-03

**Status**: Draft

**Serves**: G2, G4 · **Roadmap**: R1 · **Issue**: [#4](https://github.com/ihfc-iugg/ghfdb/issues/4)

**Input**: "Data assessors and anyone preparing heat-flow data for the GHFDB need one place to look
up what each field of the upload template means: its code and published column name, its unit,
whether it must be filled in, and which values it may take. Today that knowledge is scattered
across the template's description rows, the 2023 paper and a copied list inside the old checking
tool, and the copies disagree with the published IHFC vocabularies. A field reference, described
once in a form both people and software can read, with allowed values taken from a stated release
of the IHFC Controlled Vocabularies, gives everything later in this package, and every reader, the
same definition to work from."

## Summary

Every field of the current upload template is described once, in the **field schema**: a
Frictionless Table Schema that ships with the package. The same description is published as a
**field reference** in the documentation, one entry per field. For each field it gives the field
code, the published column name, the name and meaning, the type, the unit, the obligation, the
domain, the quality relevance, the allowed range or allowed values, and the source of every one of
those facts. The allowed values of every vocabulary field come from one stated vocabulary release,
v2026.1 of the IHFC Controlled Vocabularies, and carry each concept's URI. Moving to a newer
vocabulary release is a separate, deliberate step.

Two people use it:

- a **data assessor**, who looks a field up in the documentation;
- a **developer** using the package, who loads the field definitions from Python, and who, as a
  maintainer of this repository, moves them to a newer vocabulary release.

Out of scope: producing an upload template workbook (#5), checking a workbook (R3), cross-field
rules (R4) and the quality scheme (R5). The field schema records which part of the quality scheme a
field feeds, and nothing about how it is scored.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A data assessor looks up a field in the documentation (Priority: P1)

A data assessor preparing a workbook needs to know what a column means and what may go in it. They
open the field reference in the documentation and find the field by its field code (`C43`) or its
published column name (`tc_method`). The entry tells them what the field means, whether they must
fill it in and for which domain, its unit and type, the range or the values it accepts, and where
each of those rules comes from. For a vocabulary field it lists the allowed terms as they are
written in a cell, links each to its concept, and names the vocabulary release they come from.

**Why this priority**: This is the one place the data assessment team needs today, and the reason
the issue was raised. The scattered and disagreeing copies are the problem it removes.

**Independent Test**: Build the documentation and look up any field by its code and by its
published column name. The entry gives every fact listed above, each with its source, and its
allowed values are exactly those of the stated vocabulary release.

**Acceptance Scenarios**:

1. **Given** the documentation is built, **When** an assessor opens the field reference, **Then**
   every field of the upload template has exactly one entry, grouped as parent, child and
   assessment fields, in field-code order.
2. **Given** an assessor knows only a published column name, **When** they look for it in the
   field reference, **Then** they reach the entry for that field.
3. **Given** a field entry, **When** an assessor reads it, **Then** it gives the field code,
   published column name, name, meaning, type, unit, obligation, domain, quality relevance and
   allowed range or values, always in the same order, and names the source of each fact: Fuchs et
   al. (2023) Appendix A, the upload template, or a recorded decision.
4. **Given** a vocabulary field, **When** an assessor reads its entry, **Then** it names the
   concept scheme and the vocabulary release, and lists every allowed term in the form it takes in
   a cell, each linked to its concept's URI.
5. **Given** a field whose name in the current upload template is misspelled (`tc_pT_fuction`,
   `Ref_ISGN`), **When** an assessor reads its entry, **Then** it gives the correct published
   column name and names the misspelled form as the template's earlier spelling.
6. **Given** a field that accepts several values (lithology, stratigraphic age), **When** an
   assessor reads its entry, **Then** it says that several values may be given and how they are
   separated.
7. **Given** the field reference, **When** an assessor wants to know how it is put together,
   **Then** the page explains where its facts and allowed values come from, with a simplified
   diagram of that process.
8. **Given** the field reference, **When** an assessor wants the machine-readable form, **Then**
   the page links to the field schema for the version it documents.

---

### User Story 2 - A developer loads the field definitions (Priority: P1)

A developer building on the package, starting with the checks and the generated upload template
later in this roadmap, loads the field definitions from Python instead of copying them. They get
every field, look one up by its field code or by its published column name, and read its type,
unit, obligation, domain, range and allowed values. For a vocabulary field they get each allowed
concept with its URI, its label and its notation, the concept scheme's URI and the vocabulary
release. The same definitions are available as a Frictionless Table Schema file that any
Frictionless tool can read.

**Why this priority**: Everything after R1 is built on this description. Without it, each later
feature would carry its own copy, which is the defect being removed.

**Independent Test**: In a fresh environment with no network access, install the package, load the
field definitions and look up fields by code and by published column name. Validate the schema
file with an independent Frictionless tool.

**Acceptance Scenarios**:

1. **Given** the package is installed, **When** a developer loads the field definitions, **Then**
   they get one definition for every field of the upload template, in field-code order, with no
   network access needed.
2. **Given** the field definitions, **When** a developer looks up a field by its field code or by
   its published column name, **Then** they get the same definition either way.
3. **Given** the field definitions, **When** a developer looks up a code or name that is not a
   field, **Then** the lookup fails and names what was asked for.
4. **Given** a vocabulary field, **When** a developer reads its allowed values, **Then** each is a
   concept with its URI, label and notation, from the concept scheme the field names, in the
   stated vocabulary release.
5. **Given** the field definitions, **When** a developer asks which vocabulary release they were
   built from, **Then** they get its version and DOI.
6. **Given** the field schema file shipped with the package, **When** it is read by an
   independent Frictionless validator, **Then** it is a valid Table Schema, and every field in it
   carries its field code and its published column name.
7. **Given** a field definition, **When** a developer reads it, **Then** each fact names its
   source, as in the documentation.

---

### User Story 3 - A developer moves the field reference to a newer vocabulary release (Priority: P2)

When the IHFC Controlled Vocabularies publish a new release, a maintainer of this repository moves
the field reference to it as a change of its own. They name the release. The allowed values of
every vocabulary field are regenerated from it, the stated release is updated, and they see, field
by field, which concepts were added, removed or relabelled. Nothing else about any field changes in
that step.

**Why this priority**: Without it the allowed values freeze at v2026.1 or get edited by hand, and
the second is how the old tool drifted. It is needed before the first newer vocabulary release
appears, not before the field reference is usable.

**Independent Test**: Move the field reference from v2026.1 to a release that differs from it (a
test release is enough), and confirm the allowed values match the new release, the change lists
every difference, and no other fact moved.

**Acceptance Scenarios**:

1. **Given** the field reference built from v2026.1, **When** a maintainer moves it to a newer
   release, **Then** every vocabulary field's allowed values are those of the newer release, and
   the field schema and the field reference both name it.
2. **Given** a move to a newer release, **When** it completes, **Then** the maintainer sees, for
   each vocabulary field, the concepts added, removed and relabelled, and a field with no change
   is reported as unchanged.
3. **Given** a newer release that no longer contains a concept scheme a field names, **When** the
   maintainer moves to it, **Then** the move fails, names the field and the scheme, and changes
   nothing.
4. **Given** a move to a newer release, **When** it completes, **Then** no fact other than allowed
   values and the stated release has changed.
5. **Given** allowed values that were edited by hand, so they no longer match the stated release,
   **When** the repository's checks run, **Then** they fail and name the field.
6. **Given** the move is made, **When** the change is proposed, **Then** it is recorded in the
   changelog with the old and new release.

### Edge Cases

- A field marked mandatory for one domain only (for example C5, borehole data): the entry records
  the obligation and the domain together. Whether a given child is in that domain is decided by a
  cross-field rule (R4), not here.
- A concept scheme that serves several fields (the heat-flow corrections scheme serves C11–C19):
  each field names the scheme, and where the release groups the scheme's concepts into a
  collection for that field, the field's allowed values are that collection.
- A vocabulary term containing a comma, a slash or brackets: it is an allowed value exactly as
  published, never split or rewritten.
- `[Unspecified]` and similar terms are allowed values, not markers of missing data. The only
  missing value is an empty cell.
- A field the template's description rows give an example for rather than a range (for example
  `[Onshore (continental)]` for P7): the example is not a rule. The allowed values come from the
  vocabulary release.
- A fact on which the template and Fuchs et al. (2023) Appendix A disagree: the field reference
  follows the current template and names it as the source, and the disagreement is recorded as a
  decision.
- A field with a fixed set of values that no IHFC vocabulary publishes (P9, C9: yes, no or
  unspecified): its values are listed with their source in Appendix A, and are not vocabulary
  terms.
- A field with an open set of values and no published vocabulary (C25 lithology, C26
  stratigraphic age): no list of allowed values is given. The entry names the classification the
  paper recommends as guidance.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The package MUST describe every field of the current upload template, the 13 parent
  fields P1–P13, the 49 child fields C1–C49 and the 8 assessment fields A1–A8, in one field schema
  that is a valid Frictionless Table Schema. *(US2)*
- **FR-002**: Every field MUST carry its field code and its published column name, and both MUST be
  unique across the schema. *(US1, US2)*
- **FR-003**: Every field MUST record its name, meaning, type, unit, obligation, domain, quality
  relevance and, where the field has one, its allowed range, its format or its allowed values.
  *(US1, US2)*
- **FR-004**: Every fact recorded for a field MUST name its source: Fuchs et al. (2023) Appendix A,
  the upload template, or a decision recorded in this repository. *(US1, US2)*
- **FR-005**: The allowed values of every vocabulary field MUST be generated from a stated release
  of the IHFC Controlled Vocabularies, initially v2026.1 (DOI 10.5880/fidgeo.2026.065). No
  vocabulary term may be typed into the field schema or the code by hand. *(US2, US3)*
- **FR-006**: Every vocabulary field MUST record the URI of its concept scheme, and each allowed
  value MUST carry its concept's URI, label and notation. *(US1, US2)*
- **FR-007**: The field schema MUST record the vocabulary release it was generated from, by
  version and DOI. *(US2, US3)*
- **FR-008**: The only missing value MUST be an empty cell. A vocabulary term such as
  `[Unspecified]` MUST be recorded as an allowed value, never as missing. *(US1, US2)*
- **FR-009**: The two published column names misspelled in the current template MUST be recorded
  with their correct spelling (`tc_pT_function`, `Ref_IGSN`), with the misspelled form kept as the
  template's earlier spelling. *(US1, US2)*
- **FR-010**: A developer MUST be able to load every field definition from the installed package,
  without network access, and look a field up by field code or by published column name. An
  unknown code or name MUST fail and name what was asked for. *(US2)*
- **FR-011**: The documentation MUST contain a field reference with one entry per field, giving
  the same facts in the same order for every field, each with its source, following the reference
  rules of `docs/contributing/standards/documentation.md`. *(US1)*
- **FR-012**: The field reference MUST be reachable by field code and by published column name.
  *(US1)*
- **FR-013**: The field reference and the field schema MUST never disagree. The repository's checks
  MUST fail when they do. *(US1, US2)*
- **FR-014**: The field reference MUST explain where its facts and allowed values come from and how
  a newer vocabulary release is adopted, each with a simplified Mermaid diagram, and MUST link to
  the field schema for the version it documents. *(US1, US3)*
- **FR-015**: Moving to a newer vocabulary release MUST be a separate step that a maintainer runs
  by naming the release, that changes only allowed values and the stated release, and that reports
  per field the concepts added, removed and relabelled. *(US3)*
- **FR-016**: A move to a release that lacks a concept scheme a field names MUST fail, name the
  field and the scheme, and change nothing. *(US3)*
- **FR-017**: The repository's checks MUST fail, naming the field, when any vocabulary field's
  allowed values differ from those of the stated release. *(US3)*
- **FR-018**: `CONTEXT.md` MUST define the field reference, the assessment fields A1–A8, domain and
  quality relevance, and the field schema entry MUST describe it as built. *(US1, US2)*

### Key Entities

- **Field schema**: the one machine-readable description of every upload template field, as a
  Frictionless Table Schema. Records the vocabulary release it was generated from.
- **Field**: one entry in the field schema. Its field code, published column name, name, meaning,
  type, unit, obligation, domain, quality relevance, range or format or allowed values, and the
  source of each fact.
- **Vocabulary field**: a field whose allowed values are the concepts of one concept scheme, or of
  one collection within it, in the stated vocabulary release.
- **Allowed value**: for a vocabulary field, one concept with its URI, label, notation and the term
  it is written as in a cell. For a fixed-value field, a value with its source.
- **Vocabulary release**: the version and DOI of the IHFC Controlled Vocabularies the allowed values
  were generated from.
- **Field reference**: the documentation pages that present the field schema to a reader.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 70 fields of the current upload template have exactly one definition in the
  field schema and exactly one entry in the field reference.
- **SC-002**: For every vocabulary field, the allowed values and the concepts the stated release
  lists for it are identical: zero added, zero missing, zero relabelled.
- **SC-003**: Every recorded fact of every field names its source: zero facts without one.
- **SC-004**: An assessor can reach any field's entry from its field code or its published column
  name in one step from the field reference's opening page.
- **SC-005**: Moving to a newer vocabulary release is one step, and the resulting change touches
  nothing but allowed values, the stated release and the changelog.
- **SC-006**: The field schema passes an independent Frictionless Table Schema validator.

## Clarifications

### Session 2026-11-03

- Q: Which fields does the field reference cover: the parent and child fields only, or also the
  assessment fields A1–A8 that the current template carries? → A: All 70 fields of the template,
  A1–A8 included, grouped separately. The template is what assessors fill in, and the generated
  template (#5) needs every column. Integrated into FR-001 and US1 scenario 1.
- Q: Which spelling is recorded for the two published column names misspelled in the template? →
  A: The correct spelling, as the GHFDB portal and the vocabulary release use, with the misspelled
  form kept as the template's earlier spelling. Integrated into FR-009 and US1 scenario 5.
- Q: Where the template and Fuchs et al. (2023) Appendix A disagree on a fact, which wins? → A: The
  current template, named as the source, with each disagreement recorded as a decision. Integrated
  into Edge Cases and FR-004.
- Q: Is `[Unspecified]`, or any other term, a missing value? → A: No. An empty cell is the only
  missing value, and `[Unspecified]` is an allowed term. Integrated into FR-008 and Edge Cases.
- Q: What are the allowed values of a field with no published vocabulary? → A: A fixed set that
  the paper defines (P9, C9) is listed with its source in Appendix A. An open set (C25, C26) has no
  list, and its entry names the classification the paper recommends. Integrated into Edge Cases.

## Assumptions

- The field list is the current published upload template, sheet `data list`: row 1 field codes,
  rows 2–8 description rows. A newer template version is an ordinary change to the field
  reference, not part of this feature.
- The vocabulary release is v2026.1. Its release files are the source the allowed values are
  generated from.
- The field schema and the vocabulary terms ship inside the package, so nothing is fetched when the
  package is used.
- The field reference is read by people who do not write code. Its explanation and diagrams are
  written for them.
- How the description rows of a generated template are laid out belongs to #5, which builds on this
  feature.
