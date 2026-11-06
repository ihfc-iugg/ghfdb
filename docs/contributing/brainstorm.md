# Working notes

These notes record what was established before the package was written. They are
working notes, not decisions. Decisions are recorded as they are made, in the
specification and the decision records.

## Why a new package

The quality codes of the 2024 release of the GHFDB (Neumann et al., 2026) were
computed with the Heat Flow Quality Analysis Toolbox, `hfqa_tool` (Chishti et al.,
2025; Dergunova et al., 2026). A review of its current version in November 2026 found
defects in the scoring, a vocabulary that has drifted from the published IHFC
Controlled Vocabularies, misreported validation errors, tests that cannot detect a
wrong score, and long run times on a dataset of GHFDB size. The defects follow from
its structure, so this package is written from scratch rather than forked.

## What exists already

- **`hfqa_tool`.** Overlaps completely with `ghfdb.qc`, and is what this package
  replaces for the data assessment team.
- **The GHFDB portal's own scoring.** The portal scores the data it holds and treats
  its scores as authoritative. Its quality-score guide and decision record are the
  most complete written account of the scheme as currently applied, including where
  it departs from Fuchs et al. (2023). They are where this package's specification
  starts.
- **General validation libraries.** Frictionless (Table Schema) and pandera check
  tabular data against a declared schema. They are building blocks, not alternatives:
  neither knows the GHFDB fields, vocabularies or quality scheme.

No other software implementing the GHFDB checks or quality scheme was found.

## Who it is for

The data assessment team, working offline on their own data template workbooks before
data is submitted. The portal does not use this package: it keeps its own validation
and scoring, and recalculates every score itself.

## What it is to become

The documentation of this package is meant to become the reference for the GHFDB
validation rules and quality scheme, alongside the IHFC Controlled Vocabularies. It
starts from the scheme as the portal applies it today. Changes are proposed and agreed
in this repository's issues. Each agreed change updates the documentation, a set of
worked examples and the code together, and the portal follows the documentation.

The ideas recorded so far:

- **A versioned scheme.** A scheme release (for example "2027.1") is a fixed set of
  rules with its worked examples, released separately from the package. Each package
  release implements one scheme version and records it in its output.
- **A machine-readable field schema.** One Frictionless Table Schema describes every
  field of the data template. Allowed values for vocabulary fields are generated from
  the published vocabulary release. The schema drives the checks, the generated data
  template and the field reference pages.
- **The data template comes from this repository.** It is generated from the field
  schema for each release. The reader finds the header row by its field codes and
  skips the description rows, so older templates still work.
- **Report, never modify.** Output is a copy of the workbook with added problem and
  score columns. Near misses get a suggestion such as "did you mean `[Core samples]`?".
  An automatic fix for simple errors is a possible later addition.
