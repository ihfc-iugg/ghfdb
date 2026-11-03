# Research: A generated upload template

Investigated against `main` at the merge of FS-001, the field reference
([#7](https://github.com/ihfc-iugg/ghfdb/pull/7)).

## The specification read against FS-001

FS-001 was delivered after this specification was written. Read side by side:

- **The open risk is closed.** The field schema carries obligation, domain, quality relevance,
  name, published column name, unit and range for every field, so every description row can be
  generated (`Field.obligation`, `Field.domain`, `Field.quality_relevance`, `Field.name`,
  `Field.column_name`, `Field.unit`, `Field.minimum`/`maximum`, `Field.value_format`).
- **70 fields, not 62.** The schema holds the assessment fields `A1`–`A8` (FS-001 D-1), so row 1
  of `data list` holds `ID` and 70 field codes. The assessment fields have no obligation (D-14).
- **Two fields have a fixed set of values and no vocabulary.** P9 and C9 take `[Yes]`, `[No]` or
  `[Unspecified]` from Fuchs et al. (2023) (D-5). The specification promises a choice list on
  every vocabulary field and none on any other. Read against FS-001, the line it draws is between
  a field with a fixed list of allowed values and one without. Recorded as D-9.
- **Three fields lose the list the hand-maintained template gave them.** C20 takes free text
  (D-22). C25 and C26 have no list of allowed values (D-5). They get no choice list, and the
  differences page says so.
- **Two published column names are spelled correctly** (`tc_pT_function`, `Ref_IGSN`, D-2), and
  quality relevance is written `U-score`, `M-score`, `perturbation flags` (D-16). The description
  rows show the schema's values, and the differences page lists each change.
- **A term is written as `AllowedValue.term`**, which already carries the square brackets and the
  label or notation the field records (D-20). Allowed values are already sorted (D-21), so the
  choice lists come out in a stable order.

No acceptance scenario is contradicted. The reading above changes how FR-004 and FR-005 are
applied to P9 and C9 only.

## The hand-maintained template

`tests/sources/upload-template.xlsx` is the template the GHFDB portal distributes today, and the
reference for layout (SC-004) and for the differences page (FR-009).

- Sheets in order: `readme`, `data list`, `controlled vocabulary`.
- `data list`: `ID` in A1, the field codes in B1 onwards, row labels in A2–A8 (`Obligation`,
  `Domain`, `Quality Relevance`, `Name`, `Short Name`, `Unit`, `Allowed range of values`), empty
  from row 9. A field with no unit or no range shows `-`.
- `controlled vocabulary`: a field's terms from row 3 down, its name in row 1. The columns are
  meant to sit under the same letters as on `data list`, but from P10 onwards several are shifted
  by one: the column under P11's letter is labelled "Type of exploration method", which is P12.
  A column is matched to its field by its row 1 label, which equals the field's name on
  `data list` row 5 for every column but one, "TC averaging method", which is C48.
- Choice lists exist only on row 8, as Excel 2010 extension validations that openpyxl cannot
  read. Each references a range on `controlled vocabulary` and shows an input message holding the
  field's meaning.

## Choices

### Writing the workbook: openpyxl

| Option | Verdict |
|---|---|
| openpyxl | **Chosen.** Writes `.xlsx` with list validations that reference another sheet, accepts an error-free validation (`showErrorMessage=False`), is typed through `types-openpyxl`, and already reads the hand-maintained template in this repository's tests. Checking (R3) reads workbooks, so the package will need a workbook reader regardless. |
| XlsxWriter | Writes only. Checking would need a second library to read. |
| The standard library (`zipfile` and hand-written SpreadsheetML) | Several hundred lines of XML to keep correct for three sheets and one validation type. |

openpyxl becomes a runtime dependency (`CONSTITUTION.md` Article VII: the reason is above).
`ghfdb.fields` keeps needing nothing but the standard library, because the template is a module
of its own.

### Choice lists reference the `controlled vocabulary` sheet

A list written inline is limited to 255 characters, and C46 alone has 42 terms. Every choice list
references its field's column on `controlled vocabulary`, so there is one mechanism for every
field, the edge case of a long vocabulary needs nothing extra, and AS 1.7 (the sheet lists the same
terms the list offers) holds by construction. Each validation covers its column from row 9 to the
last row Excel has (1,048,576), with `showErrorMessage=False`, so a typed value is accepted
(FR-006).

### Columns on `controlled vocabulary` sit under their `data list` letters

The layout the hand-maintained template meant to have, without its shift. Row 1 holds the field
code, row 2 the field's name, terms from row 3, as before. A field with no list leaves its column
empty.

### Description rows

Each value comes from one attribute of the field. One marker, `-`, stands for "none" in every row,
as in the hand-maintained template, which keeps the portal's import reading what it expects:

| Row | Value |
|---|---|
| Obligation | `M`, `R` or `O`, or `-` |
| Domain | the domain codes joined by commas (`B,S`), or `-` |
| Quality Relevance | the schema's term, or `-` |
| Name | the field's name |
| Short Name | the published column name |
| Unit | the unit, or `-` |
| Allowed range of values | for a field with a minimum and a maximum, both with thousands separators and the field's decimal places, joined by ` – ` (`-999,999.9 – 999,999.9`); for a field with a value format, the format (`YYYY-MM`); otherwise `-` |

A field with allowed values shows `-` in the range row. Its values are its choice list, and the
hand-maintained template's single example term there was never a rule (FS-001 D-7).

### Reproducible content

Generation reads nothing but the field schema and the installed package's version, and iterates
in schema order, so two runs produce the same sheets, cells and validations. openpyxl stamps the
file's creation time in its document properties and its archive entries, so two files are not
byte-identical. "Identical content" (FR-011, SC-006) is read as the same sheets, cell values and
choice lists, which is what a contributor or the portal reads.

### Publishing through the documentation build

The field reference extension already copies the schema file next to its page in
`builder-inited` and links it with `{download}`. The template follows the same shape: a second
extension writes the workbook next to its page, named with the package version
(`ghfdb-upload-template-0.0.1.xlsx`), and replaces a marker line with the `{download}` link.
`sphinx-build -W` stops on any exception raised there, so a schema that cannot be read or a field
that cannot be written fails the build (FR-008). The Pages workflow already runs the build, so no
workflow changes.

### The differences page is computed

FR-009 asks for every difference from the last hand-maintained template: fields added, removed or
reordered, description rows and allowed terms that changed. Read from the two workbooks, that is
some 60 changed terms and dozens of changed cells. Written by hand it would type vocabulary terms
into a page (Article XI's intent) and could be wrong on the day it merged. The extension compares
the generated workbook with `tests/sources/upload-template.xlsx` and renders the differences as
tables, so the page is right whenever the build runs.

## What already exists

| Piece | Where the search stopped |
|---|---|
| Field facts, allowed terms, term form, sort order | this repo: `ghfdb.fields.FieldSchema`, `Field`, `AllowedValue.term` |
| Package version | the standard library: `importlib.metadata.version` |
| Column letters | an installed package: `openpyxl.utils.get_column_letter` |
| Writing sheets and list validations | an installed package: `openpyxl.Workbook`, `openpyxl.worksheet.datavalidation.DataValidation` |
| Copying a generated file next to its page and linking it | this repo: the pattern in `docs/extensions/field_reference.py` (`copy_schema`, marker replacement in `source-read`) |
| Download link in the page | Sphinx: the `{download}` role |
| Comparing two workbooks | new code: no installed package compares workbooks cell by cell and term by term |
| Refusing to replace a file | the standard library: `open(path, "xb")` semantics, raised as `FileExistsError` |
