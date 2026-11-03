# ADR 0002 — The upload template is generated, never stored

**Status:** accepted

## Decision

The upload template is built from the field schema by `ghfdb.template.UploadTemplate`, with
openpyxl, and no copy of it is kept in the repository.

- openpyxl is a runtime dependency of the package, for the template module.
- The documentation build writes the template for the version it documents beside its page and
  links it. A failure to generate the template fails the build.
- The page's list of differences from the last hand-maintained template is computed on each build,
  by comparing the generated workbook with the stored hand-maintained one in
  `tests/sources/upload-template.xlsx`.

## Why

A hand-maintained template drifts from the rules its contents are checked against, which is the
problem the template exists to solve. Generating it from the field schema on every build means
the workbook contributors download and the field reference cannot disagree, and a change to a
field or a move to a newer vocabulary release reaches the download without a hand edit.

openpyxl writes list validations that reference another sheet and accept any value, is typed,
and reads workbooks too, which checking needs. XlsxWriter only writes, and hand-written
SpreadsheetML would be several hundred lines to keep correct. Publishing through the
documentation build needs no change to the repository's workflows. A list of differences typed by
hand would repeat vocabulary terms in a page and could be wrong on the day it merged.

## Revisit if

Each released version needs a permanent address for its template, so that the documentation site
alone no longer serves it, or the GHFDB portal starts publishing a template of its own.
