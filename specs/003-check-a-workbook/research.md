# Research: Check a workbook and get a report of every problem

**Spec**: [spec.md](spec.md) · **Decisions**: [decisions.md](decisions.md)

There is no `planning-notes.md` and no sketch for this feature. The tools are chosen for the
finished package: SC-006 asks for a workbook the size of the whole GHFDB, 90,000 children with all
70 fields filled, to be checked and reported in under 15 seconds. Every measurement below was taken
on 2026-11-05, on the development machine (WSL2, 32 cores, though every step measured runs on one),
against the field schema on `main`. The test workbooks were generated in the upload template's
layout: 20,000 children written with openpyxl, and 90,000 children (21 MB, 6.3 million cells)
written with XlsxWriter, each seeded with problems of every kind.

## The time budget at 90,000 children

| Step | Chosen | Time | Rejected, and its time |
|---|---|---|---|
| Load the field schema and vocabularies | the existing `load_schema`, cache warm | 0.2 s | a cold download is 9 s, so tests and the speed test use a filled cache |
| Read the sheet | fastexcel, every cell as text, handed to pandas | 4.7 s (to polars: 5.0 s) | openpyxl: 13.5 s at 20,000, so about 60 s, and 11.7 s just to open a file with no dimension element. python-calamine to Python objects: 6.1 s, then a Python loop per cell |
| Find error cells | byte search of the sheet's XML | 0.65 s | |
| Check every field | pandas, one whole column at a time | 0.6 s for all seven rules on all 70 columns (polars: 0.3 s, same problems found) | Frictionless `validate` on rows read: 3.0 s at 20,000, so about 13 s. pandera: 0.7 s at 20,000, but wrong results (below) |
| Write the report | XlsxWriter, problems only | under 0.1 s for 900 problems; 2.3 s for 100,000 | Rewriting the workbook as a copy: 30 s with XlsxWriter, 23 s with PyExcelerate, 31 s at 20,000 with openpyxl |

The steps add up to about 6.5 s. An earlier design review ran a whole pipeline of the same shape
on polars at 8.4 s, so the speed test (D-8) is what settles the figure, inside 15 either way.
`pandas.read_excel(engine="calamine")` took 10.4 s for the same sheet and is not used. A workbook saved by Excel keeps
its text in a shared table and reads faster than the XlsxWriter-made benchmark, so the speed test
errs on the slow side.

## Reading the workbook

**Decision: fastexcel, once, with every cell as text.**

- **fastexcel** (0.21, the engine polars uses for `read_excel`) reads with calamine, in Rust,
  into Arrow, and `to_pandas()` hands that to pandas without copying text cell by cell. With `dtypes="string"` every cell arrives as the text the
  value has: `12.5` and the text `"12.5"` read the same (D-1), a number in a free-text field is
  text (D-6), a whole number stored as `3.0` reads `3`, `True` reads `true`, and a cell Excel
  holds as a date reads `2020-05-01 00:00:00`, which no year-and-month pattern matches (D-2).
  Numbers are written to at most 9 decimal places (`3.0000000001` reads `3`), which no field's
  range or decimal places reaches (D-9). A formula cell reads as the value Excel last saved for it
  and is never calculated (Article V, FR-013). A formula with no saved value, and **a cell holding
  an Excel error value** (`#N/A`, `#DIV/0!`), read as empty: see "Error cells".
- **Row and column positions.** With `skip_rows=0`, the first row of the frame is Excel row 1
  even when the sheet's first filled cell is B3, and `ColumnInfo.absolute_index` gives each
  column's sheet position. Excel row numbers are therefore exact (Article XII) from one reader.
  Without `skip_rows`, fastexcel drops leading empty rows and says nothing about it, so it is
  always passed.
- Any failure to read is a `fastexcel.FastExcelError` (`CalamineError` for a truncated or
  non-Excel file, `SheetNotFoundError` for no `data list` sheet), not an `OSError`, so the check
  turns it into its own could-not-run error.
- `.xlsx` and `.xlsm` are read. An `.xls` file is a could-not-run error naming the file.

**Error cells.** Neither fastexcel nor python-calamine returns an error value: both give an empty
cell. Reporting `#N/A` in a mandatory field as missing is what Article XII forbids, and in any
other field the value would vanish. A cell of type `e` is stored in the sheet's XML as
`<c r="B12" t="e"><v>#N/A</v></c>`, so the check scans that part of the file as bytes for such
cells and puts the error text in their place. It took 0.65 s on the 313 MB sheet of the
90,000-child workbook. A regular expression on bytes, not an XML parser, so no entity in an
untrusted file is ever expanded.

**Finding the header and the data.** The hand-maintained template (`tests/sources/upload-template.xlsx`)
and the generated one put `ID` and the field codes in row 1 and seven description rows under it,
labelled in column A (`ghfdb.template.ROW_LABELS`). The check:

1. takes as the header the first of the first 20 rows in which most non-empty cells, after the
   first filled column, name a field by code, published column name or earlier column name
   (FR-009). The first filled column is the row-label column, `ID`, and is matched to no field:
   field `A8`'s published column name is also `ID`;
2. skips every row directly under it whose first filled cell is one of the description row
   labels, compared without regard to case or surrounding spaces (D-4);
3. reads every later row as a child when at least one field's cell is filled. A row holding only
   an `ID`, or nothing, is not a child (FR-008). Cells of spaces only count as empty.

The field schema's `earlierColumnNames` already holds the two renamed columns (`tc_pT_fuction`,
`Ref_ISGN`), so recognising an earlier template's columns needs no new data.

## Checking the values

**Decision: pandas, the constitution's stack (Article XV), one whole column at a time.**

pandas and polars were measured on the same 90,000-child frame of text, with all seven rules on
all 70 columns: pandas 0.6 s, polars 0.3 s, and the same 2,340,090 problems found by both. The
difference is nothing against SC-006. pandas is kept because quality scoring (R6) will build on the
same DataFrame, and because the researchers who will read and propose rules work in pandas. The
speed came from the reader and from working on columns, never from the frame library.

Every rule the field schema holds is one operation on a text column (pandas 3, text backed by
pyarrow):

| Rule (field schema) | Operation | Problem kind |
|---|---|---|
| obligation `M` in both domains | value empty | missing |
| type `number` | `pandas.to_numeric(column.str.strip(), errors="coerce")` is missing where the text is not empty, or is infinite | wrong type |
| type `integer` | as number, and the number is not equal to its rounded value | wrong type |
| `pattern` | `str.fullmatch(pattern)` false | wrong type |
| `minimum`, `maximum` | the number outside them | out of range |
| `maxLength` | `str.len()` above it | out of range |
| `enum` | `isin(enum)` false | not in vocabulary |

Measured on single values: `3`, `3.0` and ` 12.5 ` pass a number field, `3.5` fails an integer
field, `1,234.5`, `12,5`, `true` and a date fail a number field, the text `nan` comes back missing
and `inf` infinite, so both are wrong type and never reach the range check (D-7), and the
year-and-month pattern of `C38` passes `2020-05`, `2020-05; 2021-01` and `[Unspecified]` and fails
`2020-05-01 00:00:00`. A cell gets at most one problem for its type; range, length, pattern and
vocabulary are checked only on values of the right type, so one bad cell is one problem unless it
genuinely breaks two rules (too long and not matching its pattern, say). `str.split` and `explode`
keep each value's index, so a multi-value cell is checked value by value with its Excel row.

Each operation gives the rows that break it, so the problems are built as one DataFrame per field
(Excel row, field code, kind, value) and concatenated. Nothing loops over rows (Article XIII).

**Rejected:**

- **Frictionless `validate`** (already a dependency) gets every seeded problem right, but casts row
  by row in Python: about 13 seconds at 90,000 before reading, which with reading misses SC-006.
  It also needed work-arounds of ours: its constraint name lives only in the error's free-text
  note, it rejects a number in a text field, it reports a cell of spaces as wrong type, it accepts
  `nan`, and it replaces every error of a row with all fields empty by one `blank-row` error.
- **pandera**, from its Frictionless importer, works on columns but **accepts `3.5` in a
  whole-number field** (its coercion to a nullable integer truncates it, the defect Article XII
  forbids), reports each type failure twice, raises `TypeError` inside its range check on a column
  holding text, and reports a cell of spaces as wrong type. Each would need code of ours around it,
  more than the seven expressions above.

The field schema stays a `frictionless.Schema` (ADR 0004). The check reads each field's type,
constraints and custom properties from it, and adds `required` to nothing: obligation is read from
`custom` directly.

## Writing the report

**Decision: XlsxWriter, writing a new workbook that holds the problems and the summary only.**

- Rewriting all 90,000 children into a copy took 30 s with XlsxWriter in constant-memory mode and
  23 s with PyExcelerate, and openpyxl took 31 s at 20,000. Each misses SC-006 on its own, so the
  report holds no copy of the data (D-5, spec Assumptions).
- XlsxWriter is the established writer (pandas' and polars' Excel writers both use it). 100,000 problems are
  written in 2.3 s.
- **A link from each problem to its cell was measured and dropped.** Excel allows 65,530 links in a
  sheet, and XlsxWriter took 7.3 s for 100,000 with links. The Excel row and the column name lead
  to the cell.
- **Every value from the workbook is written with `write_string`.** XlsxWriter's `write()` turns
  text starting with `=` into a formula, which Excel would run when the assessor opens the report
  (Article V).
- The report is `<name>.report.xlsx` beside the workbook. XlsxWriter writes to a temporary file in
  the same folder, which then replaces the earlier report, so a report that cannot be replaced
  (open in Excel on Windows) leaves the earlier one whole and becomes a could-not-run message.

## Suggestions

**Decision: the standard library's `difflib.get_close_matches`, with `n=1`, on distinct values
only.** Values and terms are compared after removing square brackets and surrounding spaces and
folding case, so `Core samples`, `[core samples]` and `[Core sampels]` all suggest
`[Core samples]`. An exact match after that normalising is the suggestion, otherwise the one
closest term above a ratio of 0.8. The not-in-vocabulary values of a field are made distinct
first, so a mistake repeated on 10,000 children is matched once. rapidfuzz is faster per
comparison, but the distinct values of a workbook number in the hundreds at most.

## The vocabulary release

The vocabulary files carry no version number. Every concept scheme names the release it belongs
to with `dcterms:isPartOf`, for example `https://doi.org/10.5880/fidgeo.2026.065`. The report names
the release, or releases, the schemes read for this check are part of, from the graphs
`Vocabularies` already holds after `load_schema`. Offline use (FR-014) already works:
`caching_session` keeps every downloaded file and uses it when the server cannot be reached
(`stale_if_error=True`). With nothing cached and no network, `load_schema` raises `OSError`, and a
published file missing a scheme raises `MissingSchemeError`. Both become the could-not-run message.

## Several values in one cell

Three fields have a separator (`C25`, `C26`, `C49`), and all three constrain only the cell's
length, which applies to the cell as a whole. No field with a separator has a vocabulary or a
pattern today. For one that does, the per-value check is `str.split(separator)` and `explode`
before the vocabulary or pattern expression, which keeps the Excel row of each value, so it costs
two lines in the same place. A test schema exercises it (AS 1.10).

## The command line

**Decision: `argparse`, as `ghfdb check <workbook>`**, with an entry point in `[project.scripts]`.
Exit statuses: `0` no problems, `1` problems found, `2` could not run, which is also what
`argparse` uses for a usage error.

## The speed test

SC-006 is a test (D-8). A session fixture writes the 90,000-child workbook with XlsxWriter (about
30 s, a development dependency only), and the test times `main(["check", path])` with
`time.perf_counter`, failing above 15 s. The vocabularies come from the session's filled cache, so
it times a warm load (0.2 s), never a download. It is marked `slow`, and runs by default.

## Dependencies added

| Package | Group | Why |
|---|---|---|
| `pandas[pyarrow]` | runtime | The data and the checks, on columns (Constitution, Articles XIII and XV). The extra brings pyarrow, which backs the text columns and is how fastexcel hands its frames over. Declared through the extra because no module imports pyarrow itself, which deptry would flag. |
| `fastexcel` | runtime | Reading the children in seconds. |
| `xlsxwriter` | runtime | Writing the report. |

Each is established and maintained. Frictionless, openpyxl and rdflib stay for what they already
do: the field schema, the template, the vocabularies. The check itself does not use openpyxl.

## What already exists

```
header and description rows of the template · 2, this repo   · ghfdb.template.ROW_LABELS
field by published column name               · 2, this repo   · ghfdb.fields.field_for_column
schema with allowed values                    · 2, this repo   · ghfdb.fields.load_schema
offline vocabulary cache                      · 2, this repo   · ghfdb.fields.caching_session
the sheet as text, with sheet positions        · 6, package    · fastexcel load_sheet_by_name(skip_rows=0, dtypes="string"), ColumnInfo.absolute_index
type, range, length, pattern, enum on columns · 6, package    · pandas: to_numeric, str.fullmatch, str.len, isin
the class holding the data                    · 7, new        · the maintainer's decision (D-11); no package holds a GHFDB dataset
the report                                    · 6, package    · xlsxwriter.Workbook, write_string
suggestion for a close term                   · 4, stdlib     · difflib.get_close_matches
command line                                  · 4, stdlib     · argparse
vocabulary release of a scheme                · 3, package    · rdflib graph, dcterms:isPartOf
matching a column by code or earlier name     · 7, new        · field_for_column covers the published name only
column problems                               · 7, new        · nothing reports unknown, absent or duplicate columns of this layout
the seven rule expressions                    · 7, new        · pandera and Frictionless do it wrongly or too slowly (above)
Excel error values                            · 7, new        · fastexcel and calamine read them as empty; openpyxl is 60 s
the problem record                            · 7, new        · no installed type carries an Excel row, a kind of ours and a suggestion
```
