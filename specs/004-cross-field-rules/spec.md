# Feature Specification: Check the rules that relate several fields

**Feature Branch**: `004-cross-field-rules`

**Created**: 2026-11-05

**Status**: Draft

**Serves**: G1, G4, G14 · **Roadmap**: R4 · **Depends on**: FS-003, the workbook check ([#21](https://github.com/ihfc-iugg/ghfdb/issues/21)), delivered

**Input**: [#26](https://github.com/ihfc-iugg/ghfdb/issues/26), "Check the rules that relate
several fields": some mistakes in a workbook only show when two or more fields are read together,
such as a temperature method that cannot go with the site's exploration method, a correction
recorded without the conditions it requires, or a field left empty that is mandatory only in the
child's domain. They should be found by the same check and listed in the same report as a rule
problem, against the child's Excel row and every field involved. Assessors should be able to look
up each rule in the documentation and see its source, its reasoning, a simple diagram of its logic
and a worked example. A rule that cannot name its source is not added until the data assessment
team has agreed it.

## Overview

The check (FS-003) compares each field of a child with the field schema on its own. This feature
adds the cross-field rules: rules that relate two or more fields of the same child. A data
assessor runs the same command as before, and the report now also lists a **rule problem** for
every child that breaks a rule, naming the rule and every field involved.

Every rule is written down once, in the documentation, with a short identifier that never
changes. Its entry states what the rule requires, the source it comes from, the reasoning behind
it, a simple diagram of its logic and a worked example. The worked example is also a test: the
check must find exactly the problem the example expects.

The starting set is the rules the old checking tool applied, which name no source. Each one is
traced to Fuchs et al. (2023) or to a recorded ruling before it is added. A rule that cannot be
traced is raised as an issue in this repository for the data assessment team to agree, and is not
checked until it has been.

**Out of scope**

- Rules that compare one child with another, such as parent fields that differ between the
  children of one parent.
- Quality scores (R5, R6) and inherited codes (R10).
- Fixing a broken rule in a new copy of the workbook (R12).
- Rules the data assessment team has not yet agreed. They are raised as issues and added later,
  each through its own change.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A data assessor finds the children whose fields do not fit together (Priority: P1)

A data assessor checks a workbook as before. Besides the problems with single fields, the report
now lists every child whose fields break a cross-field rule: a borehole child with no interval
bottom, a probe-sensing child with no penetration depth, a temperature method that cannot go with
the exploration method, or pT conditions that do not match the in-situ flag. Each rule problem
gives the child's Excel row, the rule it breaks, every field involved and the values found, so the
assessor can go to the cells and see what does not fit.

**Why this priority**: This is the feature. Without it these mistakes reach the data assessment
team unreported, because no single field is wrong on its own.

**Independent Test**: Check a workbook seeded with one child breaking each rule and one child
satisfying it, and compare the rule problems in the report with the ones seeded.

**Acceptance Scenarios**:

1. **Given** a child whose fields break a cross-field rule, **When** the workbook is checked,
   **Then** the report lists a rule problem for that child's Excel row, naming the rule's
   identifier and every field the rule relates, with the value found in each.
2. **Given** a child whose fields satisfy every rule, **When** the workbook is checked, **Then**
   no rule problem is reported for it.
3. **Given** a child whose exploration method makes it borehole and mine data, **When** a field
   mandatory for that domain only is empty, **Then** the report lists a rule problem naming the
   exploration method and the empty field.
4. **Given** a child whose exploration method makes it probe-sensing data, **When** a field
   mandatory for that domain only is empty, **Then** the report lists a rule problem naming the
   exploration method and the empty field.
5. **Given** a field mandatory in one domain only, **When** it is empty on a child of the other
   domain, **Then** no problem is reported for it.
6. **Given** a rule that allows only some terms in one field once another field holds a given
   term, **When** a child holds a term that is not allowed, **Then** the rule problem names that
   term.
7. **Given** a field holding several values separated by its separator, **When** a rule allows
   only some terms in it, **Then** each value is checked against the rule on its own and the
   rule problem names each value that is not allowed.
8. **Given** a child on which a field a rule depends on is empty, or already has a problem of its
   own, **When** the workbook is checked, **Then** that rule is not checked for that child, and
   the field problem is the only one reported for that mistake.
9. **Given** a child that breaks several rules, **When** the assessor reads the report, **Then**
   every broken rule is listed, each as its own rule problem.
10. **Given** any rule problem, **When** the assessor reads it, **Then** it says what the rule
    requires and shows where the rule is documented.
11. **Given** a workbook of 90,000 children with every field filled, **When** it is checked,
    **Then** the check, including every cross-field rule, and its report are finished within the
    time set in SC-006.

---

### User Story 2 - A data assessor looks up why a rule exists (Priority: P2)

A data assessor sees a rule problem they do not understand, or wants to know before filling in a
workbook which combinations of values are allowed. They open the rule in the documentation, by its
identifier from the report or from a list of every rule. The entry says what the rule requires,
which fields it relates, where it comes from and why, with a simple diagram of its logic and a
worked example showing a child that breaks it and the problem the check reports.

**Why this priority**: The rules are only trusted, and only followed, if anyone can see where they
come from (G4). An assessor who does not write code can follow each rule from its diagram (G14).

**Independent Test**: Pick any rule from a report. Find its entry from the identifier alone, and
check that it names a source, gives its reasoning, has a diagram and has a worked example whose
expected problem matches what the check reports.

**Acceptance Scenarios**:

1. **Given** the documentation, **When** an assessor opens the list of cross-field rules, **Then**
   every rule the check applies is listed, each with its identifier, the fields it relates and
   a way to its entry, and no rule is listed that the check does not apply.
2. **Given** any rule's entry, **When** an assessor reads it, **Then** it states what the rule
   requires, the fields it relates, its source, its reasoning, a diagram of its logic and a
   worked example.
3. **Given** a rule's source, **When** an assessor follows it, **Then** it names a section or
   table of Fuchs et al. (2023), or a recorded ruling.
4. **Given** a rule's worked example, **When** its child is checked, **Then** the check reports
   exactly the rule problem the example expects, and nothing more. The worked examples are run
   by the test suite, so an example that stops matching fails.
5. **Given** a field's entry in the field reference, **When** an assessor reads it, **Then** it
   lists the cross-field rules that involve the field.
6. **Given** a rule that names a concept, **When** the vocabularies as published no longer
   define that concept, **Then** the repository's checks fail and name the rule and the concept.

---

### Edge Cases

- A child whose exploration method is empty or not in the vocabulary: its domain cannot be read,
  so no domain rule is checked for it. The empty or invalid exploration method is already a
  problem of its own.
- A child whose exploration method belongs to neither domain, such as an unspecified or other
  method: no domain rule is checked for it.
- A field that holds a rule's term alongside other values, separated by its separator: the rule
  applies when any of the values is the term it names.
- A workbook from an earlier upload template that has no column for a field a rule relates: the
  column problem is reported as before, and the rule is not checked.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The check MUST apply every documented cross-field rule to every child of the
  workbook, in the same run and the same report as the field checks. (US1)
- **FR-002**: Every rule problem MUST name the child's Excel row, the rule's identifier, the field
  code and published column name of every field the rule relates, and the value found in each.
  (US1)
- **FR-003**: A child's domain MUST be read from its exploration method, by a mapping documented
  with its source. A field mandatory in one domain only MUST be checked as a rule for the children
  of that domain. (US1)
- **FR-004**: A rule MUST NOT be checked on a child when a field it depends on is empty or already
  has a field problem, so one mistake is reported once. (US1)
- **FR-005**: Every term a rule names MUST be referred to by its concept's identifier and read
  from the IHFC Controlled Vocabularies as currently published, as the field schema's allowed
  values are. No term is written into a rule by hand. (US1, US2)
- **FR-006**: Every rule MUST have a short identifier that never changes and is never reused, and
  the report MUST show where each broken rule is documented. (US1, US2)
- **FR-007**: Every rule MUST name its source: a section or table of Fuchs et al. (2023), or a
  recorded ruling. A rule with no source MUST NOT be checked. It is raised as an issue for the data
  assessment team instead. (US2)
- **FR-008**: The documentation MUST have an entry for every rule the check applies, and for no
  other, giving what it requires, the fields it relates, its source, its reasoning, a diagram of
  its logic and a worked example. (US2)
- **FR-009**: Every rule's worked example MUST be run by the test suite, and MUST produce exactly
  the rule problem it states. (US2)
- **FR-010**: The field reference MUST list, for each field, the cross-field rules that involve it.
  (US2)
- **FR-011**: Loading the rules MUST fail, naming the rule and the concept, when a concept a rule
  names is not defined in the vocabularies as published, so the repository's checks fail when
  the vocabularies change beneath a rule. (US2)
- **FR-012**: The time to check a workbook with every rule MUST meet SC-006, and MUST be measured
  by the test suite. (US1)
- **FR-013**: Adding, changing or removing a rule MUST change its documentation, its worked example
  and the check together, and MUST be recorded in `CHANGELOG.md` under **Scheme changes**. (US2)

### Key Entities

- **Cross-field rule**: a documented statement that relates two or more fields of one child, with
  an identifier, a source, its reasoning, a diagram and a worked example.
- **Rule problem**: one broken rule on one child, with the child's Excel row, the rule's
  identifier, the fields involved and the values found.
- **Domain**: borehole and mine data, or probe-sensing data, read from a child's exploration
  method.
- **Worked example**: a child's values that break one rule, with the rule problem the check must
  report for it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a workbook seeded with one child breaking each rule and one child satisfying it,
  the report lists exactly the seeded rule problems, each with its correct Excel row, rule and
  fields.
- **SC-002**: Every rule the check applies has a documentation entry with a source, reasoning, a
  diagram and a worked example, and every worked example passes.
- **SC-003**: Every rule of the old checking tool is either checked, with a source, or raised as an
  issue for the data assessment team. None is dropped without a record.
- **SC-004**: A workbook generated by this package and filled in correctly is reported with no rule
  problem.
- **SC-005**: An assessor given a rule problem from a report can find the rule's entry and say why
  the child breaks it, from the documentation alone.
- **SC-006**: The 90,000-child workbook of FS-003's SC-006 is still checked and reported in under
  15 seconds with every rule applied, on the machines the test suite runs on.

## Clarifications

### Session 2026-11-05

- Q: Where do the first rules come from? → A: The rules the old checking tool applied, about
  twenty in four groups: the exploration method and the temperature methods, the in-situ flag and
  the pT conditions, the pT conditions and the pT function, and the exploration method and the
  fields mandatory in one domain. Each is traced to a source before it is added. Integrated in the
  Overview, FR-007 and SC-003.
- Q: How is a child's domain known? → A: From its exploration method. Probing methods are
  probe-sensing data. Drilling, mining, tunnelling and indirect methods are borehole and mine
  data, as the old tool counted them. The mapping is a recorded ruling (`decisions.md`, D-1).
  Integrated as FR-003.
- Q: Is an empty field that is mandatory in one domain a missing problem or a rule problem? → A: A
  rule problem. Whether it is mandatory depends on another field, the exploration method, and the
  report must say so (`decisions.md`, D-2). Integrated as Acceptance Scenarios 1.3–1.5.
- Q: Is a rule checked when one of its fields is already wrong? → A: No. The field problem stands
  alone, so one mistake is one problem. Integrated as FR-004 and Acceptance Scenario 1.8.
- Q: How does a rule refer to vocabulary terms without typing them by hand? → A: By concept
  identifier, read from the vocabularies as currently published, the way the field schema reads its
  allowed values (FS-001). A concept that is no longer published fails the repository's checks.
  Integrated as FR-005, FR-011 and Acceptance Scenario 2.6.
- Q: Are the worked examples documentation or tests? → A: Both. Each is run by the test suite.
  Integrated as FR-009 and Acceptance Scenario 2.4.
- Q: Does a rule problem point back to its documentation? → A: Yes, by its identifier, so an
  assessor can go from the problem to the reasoning. Integrated as FR-006 and Acceptance Scenario
  1.10.
- Q: Are rules that compare children, such as parent fields that differ between children of one
  parent, part of this feature? → A: No. Every rule here relates fields of one child. Integrated in
  the out-of-scope list.

## Assumptions

- The rules apply to the fields of one child. Everything a rule needs is on the child's own row of
  the workbook, because the parent's fields are repeated on every child.
- Whether an interval's top must be no deeper than its bottom becomes a rule only if a source is
  found for it, like every other rule.
- How the report shows where a rule is documented is settled at planning. It works offline, as the
  report does.
- The glossary gains an entry for **rule**, a line saying that the domain is read from the
  exploration method, and a note under **missing** that a field mandatory in one domain only is
  reported as a rule problem.
