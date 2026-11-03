# Feature Specification: A generated upload template

**Feature Branch**: `002-upload-template`

**Created**: 2026-11-03

**Status**: Draft

**Serves**: G7, G2 · **Roadmap**: R2 · **Depends on**: FS-001, the field reference ([#4](https://github.com/ihfc-iugg/ghfdb/issues/4))

**Input**: [#5](https://github.com/ihfc-iugg/ghfdb/issues/5), "A generated upload template": data
assessors and contributors fill in the GHFDB upload template by hand, and the template is
maintained by hand too, so it drifts from the rules its contents are later checked against. A
template generated from the field reference, with its header of field codes, its description rows
and a choice list for every vocabulary field, means the workbook people fill in and the checks
that read it always agree. Each version should be downloadable from the documentation site.

## Overview

The upload template stops being a hand-maintained file. This repository generates it from the
field schema (FS-001) for each version of the package: the header of field codes, the description
rows and a choice list on every vocabulary field, with the allowed terms of the stated vocabulary
release. A data assessor or contributor downloads it from the documentation site. A developer can
generate the same template with the package.

The layout stays that of the upload template distributed today, so existing contributors and the
GHFDB portal's import recognise it: the sheets `readme`, `data list` and `controlled vocabulary`,
and on `data list` the field codes in row 1 with `ID` first, the description rows in rows 2–8 and
data from row 9.

**Out of scope**

- Describing the fields themselves. Every field fact (code, published column name, type, unit,
  obligation, range, allowed values) is FS-001's. This feature reads that description and never
  restates it.
- Checking a workbook, including reading templates from earlier versions (R3).
- Other spreadsheet layouts, such as the GHFDB release format.
- A permanent address for each version's template (R13).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A data assessor downloads the upload template and fills it in (Priority: P1)

A data assessor, or anyone contributing heat-flow data, opens the documentation site, downloads
the upload template and fills it in. Every column is a field of the field schema, the description
rows tell them what each field needs, and every vocabulary field offers a choice list of the terms
they may enter. What they fill in is what the checks will later read, because both come from the
same field schema.

**Why this priority**: This is the reason the feature exists. A hand-maintained template is where
the drift between what people fill in and what is checked begins.

**Independent Test**: Build the documentation, follow the site's link to the template, open the
file, and compare its columns, description rows and choice lists with the field schema of the
same version.

**Acceptance Scenarios**:

1. **Given** the documentation site for a version of the package, **When** a contributor follows
   its link to the upload template, **Then** they download the template generated for that
   version.
2. **Given** the downloaded template, **When** a contributor opens the `data list` sheet,
   **Then** row 1 holds `ID` followed by the field code of every field in the field schema, once
   each, in the field schema's order, and no other column.
3. **Given** the `data list` sheet, **When** a contributor reads rows 2–8 under a field code,
   **Then** they hold that field's obligation, domain, quality relevance, name, published column
   name, unit and allowed range, in that order, each taken from the field schema, with column A
   naming each row.
4. **Given** a field whose allowed values come from a controlled vocabulary, **When** a
   contributor selects a data cell in its column on any row from row 9 down, **Then** the cell
   offers a choice list holding exactly the terms of that vocabulary in the stated vocabulary
   release, written as a term is written in a workbook cell (its label or notation in square
   brackets).
5. **Given** a field with no controlled vocabulary, **When** a contributor selects a data cell in
   its column, **Then** no choice list is offered.
6. **Given** a vocabulary field, **When** a contributor types a value that is not on its choice
   list, **Then** the spreadsheet accepts it, and the value is left for the check to report.
7. **Given** the `controlled vocabulary` sheet, **When** a contributor reads it, **Then** it lists
   the allowed terms of every vocabulary field, the same terms its choice list offers.
8. **Given** the downloaded template, **When** a contributor reads its `readme` sheet, **Then** it
   states the package version and the vocabulary release the template was generated from, and
   points to the field reference in the documentation.
9. **Given** a contributor who has used the hand-maintained template, **When** they read the
   template's page in the documentation, **Then** it lists every way the generated template
   differs from the last hand-maintained one: fields added, removed or reordered, and description
   rows or allowed terms that changed.
10. **Given** a change to the field schema or a move to a newer vocabulary release, **When** the
    documentation is next built, **Then** the template it links reflects the change with no hand
    edit to the template.

---

### User Story 2 - A developer generates the upload template with the package (Priority: P2)

A developer using the `ghfdb` package generates the upload template themselves, from the field
schema of the version they have installed, and writes it to a file of their choosing. They get the
same template the documentation site publishes for that version.

**Why this priority**: The published download serves contributors. Generating it from the package
serves anyone building on `ghfdb`, such as a tool that hands contributors a template, and it is the
same generation the documentation build relies on.

**Independent Test**: With the package installed, generate the template to a new file and compare
its content with the template the documentation build publishes for the same version.

**Acceptance Scenarios**:

1. **Given** the installed package, **When** a developer generates the upload template to a path,
   **Then** a template meeting every scenario of User Story 1 is written there.
2. **Given** a version of the package, **When** a developer generates the template twice, or
   compares their template with the one the documentation site publishes for that version,
   **Then** the content is identical.
3. **Given** a path where a file already exists, **When** a developer generates the template there
   without asking to replace it, **Then** nothing is written, the existing file is untouched and
   the developer is told why.
4. **Given** a path where a file already exists, **When** a developer generates the template there
   and asks to replace it, **Then** the file is replaced with the template.
5. **Given** the package's documentation, **When** a developer looks up how to generate the
   template, **Then** a reference entry describes the interface, its arguments and what it writes.

---

### Edge Cases

- A vocabulary field whose vocabulary holds more terms than a spreadsheet can carry in a choice
  list written inline: its choice list still offers every term, read from the
  `controlled vocabulary` sheet.
- A field that may hold more than one term: the choice list offers single terms, and a combination
  is typed (Acceptance Scenario 1.6), as the field schema allows.
- A field with no unit or no range: its description cell shows that the field has none, in one
  form used for every such field.
- A field added to or removed from the field schema in a later version: it appears in or
  disappears from that version's template with no hand edit.
- The field schema cannot be read, or a vocabulary field names a vocabulary the release does not
  hold: generation fails with a message naming the field, and the documentation build fails with
  it rather than publishing a template that disagrees with the field schema.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The upload template MUST be generated entirely from the field schema of the package
  version. No field code, description, unit, range or term is written into the generator by hand.
  (US1, US2)
- **FR-002**: The template MUST have the sheets `readme`, `data list` and `controlled vocabulary`.
  On `data list`, row 1 MUST hold `ID` then every field code in the field schema's order, rows
  2–8 the description rows Obligation, Domain, Quality Relevance, Name, Short Name, Unit and
  Allowed range with column A naming each row, and data MUST start at row 9. (US1)
- **FR-003**: Every description row value MUST come from the field schema, so a description row
  cannot disagree with the rule the check applies. (US1)
- **FR-004**: Every vocabulary field MUST offer a choice list on every data row from row 9 down,
  holding exactly the terms of its vocabulary in the stated vocabulary release, written as terms
  are written in a workbook cell. The `controlled vocabulary` sheet MUST list the same terms. (US1)
- **FR-005**: A field with no controlled vocabulary MUST have no choice list. (US1)
- **FR-006**: A choice list MUST NOT reject a value that is not on it. Reporting it is the check's
  job. (US1)
- **FR-007**: The `readme` sheet MUST state the package version and the vocabulary release the
  template was generated from, and point to the field reference. (US1)
- **FR-008**: The documentation build MUST generate the template and the documentation site MUST
  link to it from a page about the template. The build MUST fail when the template cannot be
  generated. (US1)
- **FR-009**: The template's documentation page MUST list how the generated template differs from
  the last hand-maintained one. (US1)
- **FR-010**: The package MUST let a developer generate the template to a path they give. It MUST
  NOT replace an existing file unless asked to, and MUST say why when it declines. (US2)
- **FR-011**: Generating the template for one package version MUST always produce the same
  content, and the template the documentation site publishes MUST be that content. (US1, US2)
- **FR-012**: The interface that generates the template MUST have a reference entry in the
  documentation, and the change MUST be recorded in `CHANGELOG.md`. (US2)

### Key Entities

- **Upload template**: the generated spreadsheet, one per package version, with its three sheets.
  It carries the package version and the vocabulary release it came from.
- **Field schema** (FS-001): the description of every field, which the template is generated from.
  It is read, never restated.
- **Choice list**: the terms a contributor can pick in a vocabulary field's cells, the allowed
  terms of that field's vocabulary in the stated vocabulary release.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every field of the field schema appears exactly once in row 1 of the generated
  template, in the field schema's order, and no column appears that the field schema does not
  hold apart from `ID`.
- **SC-002**: Comparing every description row cell of the generated template with the field
  schema finds no disagreement.
- **SC-003**: For every vocabulary field, the choice list holds every term of its vocabulary in
  the stated vocabulary release and nothing else: none missing, none extra.
- **SC-004**: The generated template has the same sheet names, the same row 1 label in column A,
  the same description row names in rows 2–8 and the same first data row as the upload template
  the GHFDB portal distributes today, so a contributor or the portal's import that knows that
  template finds every part of this one where it expects it.
- **SC-005**: A contributor reaches the template download from the documentation site's home page
  in no more than two links.
- **SC-006**: The template the documentation site publishes for a version and the one a developer
  generates with that version are identical in content.

## Clarifications

### Session 2026-11-03

- Q: Does a choice list stop a contributor entering a value that is not on it? → A: No. It offers
  the allowed terms and accepts anything typed. Blocking would hide the problem from the check,
  which reports a value not in the vocabulary as exactly that (README, "A problem is reported
  exactly as it is"). Integrated as Acceptance Scenario 1.6 and FR-006.
- Q: On which rows does a vocabulary field offer its choice list? → A: On every data row from row
  9 down, so a contributor never runs out of rows that offer it. The template has no pre-numbered
  empty rows. Integrated as Acceptance Scenario 1.4 and FR-004.
- Q: How does someone holding a template know which version and vocabulary release it came from?
  → A: The `readme` sheet states both and points to the field reference. Integrated as Acceptance
  Scenario 1.8 and FR-007.
- Q: "Each version should be downloadable from the documentation site": which versions? → A: The
  documentation site links the template generated for the version it documents. A permanent
  address for every earlier version's template is R13. Integrated as Acceptance Scenario 1.1.
- Q: Through which interface does a developer generate the template? → A: The `ghfdb` Python
  interface. The package has no command line yet, and a command for the template can be added to
  this specification when the command line arrives with checking (R3). Integrated as User Story 2.

## Assumptions

- The field schema (FS-001) carries, for every field, the facts the description rows show:
  obligation, domain, quality relevance, name, published column name, unit and allowed range. Where
  it does not, the missing fact is added to the field schema, never to this feature.
- The documentation site is built from the default branch, so "the version it documents" is the
  version on the default branch until per-version documentation exists.
- The template is generated during the existing documentation build, so publishing it needs no
  change to the repository's workflows.
- The upload template the GHFDB portal distributes today is the reference for the layout. Its
  description values are not: where the field schema disagrees with them, the field schema wins and
  the difference is listed (FR-009).
