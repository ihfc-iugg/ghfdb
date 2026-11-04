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
once in a form both people and software can read, with allowed values taken from the published IHFC
Controlled Vocabularies, gives everything later in this package, and every reader, the
same definition to work from."

## Summary

Every field of the current upload template is described once, in the **field schema**: a
Frictionless Table Schema that ships with the package. The same description is published as a
**field reference** in the documentation, one entry per field. For each field it gives the field
code, the published column name, the name and meaning, the type, the unit, the obligation, the
domain, the quality relevance, the allowed range or allowed values, and the source of every one of
those facts. The allowed values of every vocabulary field come from the IHFC Controlled Vocabularies as
currently published, and carry each concept's URI. The field schema holds no vocabulary term and
states no release or version: it links each vocabulary field to the permanent identifier of its
concept scheme and, where there is one, its collection, and the terms are read from the file
published at the identifier when the schema is loaded.

Two people use it:

- a **data assessor**, who looks a field up in the documentation;
- a **developer** using the package, who loads the field definitions from Python, and who, as a
  maintainer of this repository, hears when the vocabularies change.

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
written in a cell, links each to its concept, and links the vocabulary they come from.

**Why this priority**: This is the one place the data assessment team needs today, and the reason
the issue was raised. The scattered and disagreeing copies are the problem it removes.

**Independent Test**: Build the documentation and look up any field by its code and by its
published column name. The entry gives every fact listed above, each with its source, and its
allowed values are exactly those the vocabulary publishes.

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
   concept scheme and collection it links to, and lists every allowed term in the form it takes in
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
concept with its URI, its label and its notation, the identifiers of the concept scheme and collection
it comes from. The same definitions are available as a Frictionless Table Schema file that any
Frictionless tool can read.

**Why this priority**: Everything after R1 is built on this description. Without it, each later
feature would carry its own copy, which is the defect being removed.

**Independent Test**: In a fresh environment, install the package, load the field definitions and
look up fields by code and by published column name. Build the complete Frictionless Table Schema
and validate it with an independent Frictionless tool. Load the definitions again with no network
access and confirm they load.

**Acceptance Scenarios**:

1. **Given** the package is installed, **When** a developer loads the field definitions, **Then**
   they get one definition for every field of the upload template, in field-code order. The first
   load downloads the vocabulary files into a cache directory, and later loads need no network
   access.
2. **Given** the field definitions, **When** a developer looks up a field by its field code or by
   its published column name, **Then** they get the same definition either way.
3. **Given** the field definitions, **When** a developer looks up a code or name that is not a
   field, **Then** the lookup fails and names what was asked for.
4. **Given** a vocabulary field, **When** a developer reads its allowed values, **Then** each is a
   concept with its URI, label and notation, from the concept scheme and collection the field
   names, as currently published. The members of an ordered collection keep its order.
5. **Given** the field definitions, **When** a developer reads a vocabulary field, **Then** it
   gives the permanent identifiers of its concept scheme and collection, and no version or DOI is
   stated anywhere in the field definitions.
6. **Given** the field schema file shipped with the package, **When** a developer builds the
   complete Table Schema from it and reads that with an independent Frictionless validator,
   **Then** it is a valid Table Schema with an `enum` on every field that has allowed values, and
   every field in it carries its field code and its published column name.
7. **Given** a field definition, **When** a developer reads it, **Then** each fact names its
   source, as in the documentation.

---

### User Story 3 - A developer finds out when the vocabularies change (Priority: P2)

The IHFC Controlled Vocabularies are published at permanent identifiers, and data assessors do not
choose which version of them they use. The field schema links each vocabulary field to its
identifiers and states no release, version or DOI. When the vocabularies change, the allowed values
change with them, and the repository's checks fail, so the maintainer hears about it the day it
happens and deals with what depended on a term that moved.

**Why this priority**: Without it the allowed values freeze or get edited by hand, and the second
is how the old tool drifted. It is needed before the vocabularies first change, not before the
field reference is usable.

**Independent Test**: Point a vocabulary field at a scheme or collection its published file does
not define, and confirm loading fails and names the field. Read the real published files and
confirm every identifier the field schema holds is defined in them.

**Acceptance Scenarios**:

1. **Given** the vocabularies change a term, **When** the field definitions are next loaded,
   **Then** the field's allowed values are the new ones and the field schema file has not changed.
2. **Given** the repository's checks run, **When** they load the field schema, **Then** they read
   the files as currently published, never a copy kept from an earlier run, and fail when a scheme
   or collection the field schema links to is not defined in the file at its identifier.
3. **Given** a scheme or collection that is no longer defined where it is published, **When** the
   field definitions are loaded, **Then** loading fails and names the field and the missing
   identifier.
4. **Given** a cached copy of a vocabulary file more than a week old, **When** the field
   definitions are loaded, **Then** the file is downloaded again, and the old copy stays in use
   when the download fails.

### Edge Cases

- A field marked mandatory for one domain only (for example C5, borehole data): the entry records
  the obligation and the domain together. Whether a given child is in that domain is decided by a
  cross-field rule (R4), not here.
- A concept scheme that serves several fields (the heat-flow corrections scheme serves C11–C19):
  each field names the scheme, and where the vocabularies group the scheme's concepts into a
  collection for that field, the field's allowed values are that collection.
- A vocabulary term containing a comma, a slash or brackets: it is an allowed value exactly as
  published, never split or rewritten.
- `[Unspecified]` and similar terms are allowed values, not markers of missing data. The only
  missing value is an empty cell.
- A field the template's description rows give an example for rather than a range (for example
  `[Onshore (continental)]` for P7): the example is not a rule. The allowed values come from the
  published vocabulary.
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
- **FR-005**: The allowed values of every vocabulary field MUST be read from the IHFC Controlled
  Vocabularies as currently published at their permanent identifiers, when the field schema is
  loaded. No vocabulary term or list of values may be written in the field schema file or typed
  into the code. *(US2, US3)*
- **FR-006**: Every vocabulary field MUST link to the permanent identifier of its concept scheme
  (such as `https://w3id.org/ihfc-iugg/vocabularies/exploration-methods`) and, where the
  vocabularies narrow the choice, to the identifier of its collection or ordered collection (such
  as `https://w3id.org/ihfc-iugg/vocabularies/heat-flow-corrections/insitu`). Each allowed value
  MUST carry its concept's URI, label and notation. *(US1, US2)*
- **FR-007**: The field schema MUST NOT state a release, version or DOI of the vocabularies.
  Data assessors do not choose which version they use. *(US2, US3)*
- **FR-008**: The only missing value MUST be an empty cell. A vocabulary term such as
  `[Unspecified]` MUST be recorded as an allowed value, never as missing. *(US1, US2)*
- **FR-009**: The two published column names misspelled in the current template MUST be recorded
  with their correct spelling (`tc_pT_function`, `Ref_IGSN`), with the misspelled form kept as the
  template's earlier spelling. *(US1, US2)*
- **FR-010**: A developer MUST be able to load every field definition from the installed package
  and look a field up by field code or by published column name. A vocabulary file MUST be
  downloaded from its scheme's identifier with `.ttl` added on first use, into a cache directory
  outside the repository named for the scheme, and read from the cache after that, with no network
  access. A cached file older than a week MUST be downloaded again, and the old copy kept when
  that fails. The package MUST NOT contain the vocabulary files. An unknown code or name MUST fail
  and name what was asked for. *(US2)*
- **FR-011**: The documentation MUST contain a field reference with one entry per field, giving
  the same facts in the same order for every field, each with its source, following the reference
  rules of `docs/contributing/standards/documentation.md`. *(US1)*
- **FR-012**: The field reference MUST be reachable by field code and by published column name.
  *(US1)*
- **FR-013**: The field reference and the field schema MUST never disagree. The repository's checks
  MUST fail when they do. *(US1, US2)*
- **FR-014**: The field reference MUST explain where its facts and allowed values come from and
  how they stay current, each with a simplified Mermaid diagram, and MUST link to the field schema
  for the version it documents. *(US1, US3)*
- **FR-015**: Changing the vocabularies MUST NOT require a change to the field schema file, unless
  a scheme or collection is renamed, which is a hand edit of its identifier. *(US3)*
- **FR-016**: Loading a field schema that links to a scheme or collection its published file does
  not define MUST fail and name the field and the identifier. *(US3)*
- **FR-017**: The repository's checks MUST read the vocabularies as currently published, never a
  copy kept from an earlier run, so that they fail when the vocabularies change beneath the field
  schema. They MUST fail when a scheme or collection the field schema links to is not defined in
  the file at its identifier. *(US3)*
- **FR-019**: The complete Frictionless Table Schema, with an `enum` on every field that has
  allowed values, MUST be built in memory from the field schema and the published vocabularies, and
  MUST NOT be stored in the repository. The documentation MUST offer that complete schema for
  download. *(US2)*
- **FR-018**: `CONTEXT.md` MUST define the field reference, the assessment fields A1–A8, domain and
  quality relevance, and the field schema entry MUST describe it as built. *(US1, US2)*

### Key Entities

- **Field schema**: the one machine-readable description of every upload template field, as a
  Frictionless Table Schema file written by hand. Links each vocabulary field to its vocabulary and holds
  no vocabulary term and no release or version.
- **Field**: one entry in the field schema. Its field code, published column name, name, meaning,
  type, unit, obligation, domain, quality relevance, range or format or allowed values, and the
  source of each fact.
- **Vocabulary field**: a field whose allowed values are the concepts of one concept scheme, or of
  one collection within it, as currently published. The field links to the scheme and the
  collection.
- **Allowed value**: for a vocabulary field, one concept with its URI, label, notation and the term
  it is written as in a cell. For a fixed-value field, a value with its source.
- **Vocabulary identifier**: the permanent address of a concept scheme or collection of the IHFC
  Controlled Vocabularies, where its Turtle file is published with `.ttl` added.
- **Field reference**: the documentation pages that present the field schema to a reader.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 70 fields of the current upload template have exactly one definition in the
  field schema and exactly one entry in the field reference.
- **SC-002**: For every vocabulary field, the allowed values and the concepts the vocabularies
  currently publish for it are identical: zero added, zero missing, zero relabelled. They are
  read from the published files, so they cannot differ.
- **SC-003**: Every recorded fact of every field names its source: zero facts without one.
- **SC-004**: An assessor can reach any field's entry from its field code or its published column
  name in one step from the field reference's opening page.
- **SC-005**: A change in the vocabularies reaches the allowed values with no edit to the field
  schema, and the repository's checks report it.
- **SC-006**: The field schema passes an independent Frictionless Table Schema validator.

## Clarifications

### Session 2026-11-03

- Q: Which fields does the field reference cover: the parent and child fields only, or also the
  assessment fields A1–A8 that the current template carries? → A: All 70 fields of the template,
  A1–A8 included, grouped separately. The template is what assessors fill in, and the generated
  template (#5) needs every column. Integrated into FR-001 and US1 scenario 1.
- Q: Which spelling is recorded for the two published column names misspelled in the template? →
  A: The correct spelling, as the GHFDB portal and the vocabularies use, with the misspelled
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
- The vocabularies are published at `https://w3id.org/ihfc-iugg/vocabularies/<scheme>`, which
  redirects to the scheme's Turtle file when `.ttl` is added. Collections are defined inside the
  scheme's file at `<scheme>/<collection>`.
- The field schema ships inside the package. The vocabulary files do not: the package downloads
  each file when it is needed, and a cached file works without network access.
- The field reference is read by people who do not write code. Its explanation and diagrams are
  written for them.
- How the description rows of a generated template are laid out belongs to #5, which builds on this
  feature.
