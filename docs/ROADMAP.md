# Roadmap

**Date:** 2026-11-03

This document was designed against [GOALS.md](../GOALS.md). See also [CONTEXT.md](../CONTEXT.md)
for domain terminology and [CONSTITUTION.md](../CONSTITUTION.md) for project standards.

## Versioning

| Version | Gate |
|---|---|
| `0.0.x` | Building toward the Essential goals. Pre-viable, expect churn, nothing published. |
| `0.1.0` | Every Essential goal delivered. The minimum usable release, and the first published to PyPI. |
| `0.1.x` to `0.x` | Advancing the Expected goals, at whatever granularity the work takes. Patches are fixes. |
| `1.0.0` | Every Expected goal delivered. The complete, dependable release. |
| `1.x` | The stable line: fixes and additive features only. |
| `2.0` | The next major release, for breaking changes. |

A goal is not one minor release. Some take several, and one minor release can move two. Once
`1.0` ships, a breaking change never goes out as `1.x`. It waits for the next major release.

Aspirational goals may be developed against v2 or v1 as required.

## Essential goals: v0.1.0

Everything needed for an assessor to check a workbook and preview its scores with confidence.

### R1 — A field reference built from the published vocabularies

*delivered in [#4](https://github.com/ihfc-iugg/ghfdb/issues/4) · advances G2, G4*

Every field of the upload template is described once, in a form both people and software can
read: its code, its published column name, what it means, its unit, whether it is mandatory, the
values it may take and where each rule comes from. The allowed values of every vocabulary field
come from a stated release of the IHFC Controlled Vocabularies. Everything later is built on this
description, so it comes first.

**Deliverables:**

- A machine-readable description of every upload template field.
- Allowed values for every vocabulary field taken from a stated vocabulary release, with no term
  typed in by hand.
- A field reference in the documentation, one entry per field, with the source of each rule.
- A clear, separate step for moving to a newer vocabulary release.

Serves G2 and G4. Out of scope: checking workbooks (R3), and the template itself (R2).

### R2 — A generated upload template

*delivered in [#5](https://github.com/ihfc-iugg/ghfdb/issues/5) · advances G7, G2*

The upload template is generated from the field reference rather than maintained by hand: its
header of field codes, its description rows and a choice list for every vocabulary field. It
comes straight after the field reference, so that the workbooks assessors fill in and the checks
that read them come from the same description, and the template can never drift from the rules.
Each release publishes the template, linked from the documentation site.

**Deliverables:**

- An upload template generated from the field reference, with its description rows.
- A choice list for every vocabulary field, taken from the stated vocabulary release.
- The generated template published with each release and linked from the documentation.
- Older templates still readable by the checks, with any differences from the current one noted.

Serves G7 and G2. Out of scope: other spreadsheet layouts, such as the release format.

### R3 — Checking a workbook field by field

*delivered in [#21](https://github.com/ihfc-iugg/ghfdb/issues/21) · advances G1, G2*

An assessor runs one command on an upload template workbook and gets back a copy of it with every
problem listed against its row: a mandatory field left empty, text where a number belongs, a
fraction in a whole-number field, a value out of range, or a term that is not in the vocabulary,
with a suggestion when the value is close to one. Each problem names its Excel row, its field and
its kind, and the original workbook is never changed. This is the first thing the data assessment
team can use.

**Deliverables:**

- A command that checks a workbook and writes a report copy beside it.
- Every problem reported as what it is, with its Excel row number and field.
- Suggestions for values that are close to a vocabulary term.
- Workbooks with a different number of description rows, or empty pre-numbered rows, read
  correctly.
- A reference page for the command and the report layout.

Serves G1 and G2. Out of scope: rules that relate several fields (R4), and scores (R6).

### R4 — Cross-field rules

*delivered in [#26](https://github.com/ihfc-iugg/ghfdb/issues/26) · advances G1, G4*

Some mistakes only show when two fields are read together, for example a temperature method that
cannot go with the stated exploration method, or a correction recorded without the conditions it
requires. Each such rule is written down with its source and a worked example, and the check
reports a broken rule against the row and fields involved.

**Deliverables:**

- Every cross-field rule documented, with its source, its reasoning and a diagram of its logic.
- Each rule checked, and reported as a rule problem naming the fields involved.
- A worked example for each rule.

Serves G1 and G4. Out of scope: any rule that cannot name a source; such a rule is raised as an
issue for the data assessment team to agree first.

### R5 — The quality scheme, written down

*delivered in [#37](https://github.com/ihfc-iugg/ghfdb/issues/37) · advances G4, G5, G3*

The quality scheme is set out in the documentation as a complete specification: the U-score, the
T-score and TC-score for probe-sensing and for borehole and mine data, the M-score, the
perturbation flags, the quality code and the inherited code of a parent. It starts from the scheme
as the GHFDB portal applies it today. Every rule names its source in Fuchs et al. (2023) or the
ruling that changed it, and a page lists every departure from the paper with its reasoning. The
worked examples are published with it, each one a case the GHFDB portal's own tests assert. The
scheme is living documentation: questions where the paper is ambiguous or contradicts itself are
raised with the data assessment team in this repository's issues, and the pages are updated as
each is settled.

**Deliverables:**

- A specification page for each part of the scheme, with a diagram of each decision.
- Every departure from the 2023 paper recorded, with its reasoning.
- A set of worked examples, agreed with the GHFDB portal, giving each example's inputs and its
  expected scores.
- The open questions raised with the data assessment team in this repository's issues.

Serves G4, G5 and G3. Out of scope: publishing the scheme as a citable release (R8).

### R6 — Preview quality scores for each child

*multi-feature · advances G3*

The check also scores every child: its U-score, its T-score and TC-score, its M-score with the
missing-information mark, its perturbation flags and its quality code, written into the report,
which names the package version that made them until the scheme has numbered releases (R8).
Every worked example from R5 produces exactly its
expected scores.

**Deliverables:**

- Each part of the scheme computed for every child in a workbook.
- The scores in the report, with the package version that made them.
- Every worked example passing with its exact expected scores.

Serves G3. Out of scope: the parent's inherited code (R10).

## Expected goals: v1.0.0

What a complete, dependable version adds, once the minimum usable release is in use.

### R7 — A step-by-step guide for assessors

*feature · advances G10, G14*

A tutorial takes an assessor who has never used a terminal from installing the package to reading
their first report, with an explanation of each part of the report and how to act on it.

**Deliverables:**

- An installation and first-check tutorial written for a reader who does not code.
- How-to guides for the common jobs, such as checking a new workbook and reading a problem.
- An overview of how a workbook is checked and scored, drawn as simple diagrams.

Serves G10 and G14. Out of scope: any interface other than the command line.

### R8 — Citable scheme releases

*feature · advances G6, G5*

The quality scheme is released in its own numbered versions, separately from the package. Each
release fixes the rules and their worked examples, can be cited, and is what the GHFDB portal and
any other implementation test against. Every report records the scheme version it was scored
under.

Serves G6 and G5.

### R9 — Replacing hfqa_tool

*resolve · advances G1, G3*

The data assessment team moves from `hfqa_tool` to this package, with a note on what changed in
the checks and scores, and the old tool is marked as superseded.

Serves G1 and G3. Out of scope: converting the team's own spreadsheet layouts.

### R10 — Inherited parent codes

*feature · advances G8*

The report shows the quality code each parent inherits from its relevant children, with the rule
for grouping children under their parent documented and shown as a diagram.

Serves G8.

### R11 — GHFDB-scale performance

*feature · advances G9*

A workbook the size of the whole GHFDB is checked and scored in seconds, and that is measured on
every change so it stays true.

Serves G9.

## Aspirational goals: v2.0

Genuine wants that the package is complete without.

### R12 — Fixing simple errors automatically

*feature · advances G11*

A separate command writes a new copy of a workbook with the simplest problems corrected, such as a
term in the wrong case or without its brackets, and lists every change it made.

Serves G11.

### R13 — Persistent addresses

*resolve · advances G12*

The documentation, each scheme version and the field reference have permanent addresses that do
not depend on where the site is hosted.

Serves G12.
