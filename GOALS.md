# Goals

These are the standing directions `ghfdb` works toward. Each one is a capability or
quality to steer by, not a task that gets ticked off. Whether any goal has been served well enough
is decided in the roadmap, the feature specs, and review, never by the goal itself.

This file carries no version numbers or release plan; that lives in the roadmap. For what the
package is, what it stays out of, and the principles that settle a close call, read the
*Scope & philosophy* section of the [README](README.md).

Importance is a tag on each goal, not a ranking:

- **Essential** — not worth adopting without it.
- **Expected** — a complete, dependable version is expected to have it.
- **Aspirational** — a genuine want whose absence never makes the package incomplete.

| ID | Goal | Importance | Status | Notes |
|----|------|------------|--------|-------|
| G1 | An assessor can check an upload template workbook and get every problem reported exactly as it is, with its Excel row and field | Essential | | |
| G2 | Allowed values are always those the IHFC Controlled Vocabularies currently publish at their permanent identifiers | Essential | | |
| G3 | Preview quality scores agree with the GHFDB portal's for the same data | Essential | | |
| G4 | Every validation rule and quality rule is documented and traceable to its source | Essential | | |
| G5 | The documentation is the reference for the GHFDB validation rules and quality scheme, superseding Fuchs et al. (2023) | Essential | | |
| G6 | The quality scheme is released in citable versions, with worked examples any implementation can test against | Expected | | |
| G7 | The upload template is generated from the field schema for each release | Essential | | |
| G8 | Parents' inherited quality codes appear in the report | Expected | | |
| G9 | A dataset the size of the GHFDB is checked and scored in seconds | Expected | | |
| G10 | Assessors who do not write code can install and run it from the command line by following a step-by-step guide | Expected | | |
| G11 | Simple errors can be fixed automatically, into a new copy of the workbook | Aspirational | | |
| G12 | Documentation and schema versions have persistent addresses | Aspirational | | |
| G13 | The package grows tools for working with the GHFDB beyond quality control | Aspirational | | |
| G14 | A reader who does not write code can follow every check, rule and scoring process through simplified diagrams | Expected | | |

_Written 2026-11-03. Revise as the goals change._
