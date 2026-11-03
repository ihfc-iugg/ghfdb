# Decisions — FS-002: A generated upload template

## Decided by the maintainer

- **This repository owns the upload template.** It is generated from the field schema for each
  version and distributed as a download linked from the documentation site.
- **The template is generated and published through the documentation build.** The repository's
  workflows are not changed by this feature.
- **Description rows are generated from the field schema**, so they cannot disagree with the rules
  the check applies.
- **The layout follows the upload template distributed today**: sheets `readme`, `data list` and
  `controlled vocabulary`; on `data list`, row 1 holds the field codes with `ID` first, rows 2–8
  the description rows Obligation, Domain, Quality Relevance, Name, Short Name, Unit and Allowed
  range, and data starts at row 9. Keeping it lets existing contributors and the GHFDB portal's
  import recognise the generated template.
- **The template serves two people with separate stories**: contributors who download and fill it
  in, and developers who generate it with the package.

## Resolved while specifying

1. **A choice list offers terms and blocks nothing.** A spreadsheet can reject a value that is not
   on its list, or only offer the list. Rejecting would stop a contributor recording what the
   publication says and would hide the problem from the check, which exists to report it as
   "not in vocabulary". Offering the list keeps every problem visible to the check.
2. **Choice lists cover every data row from row 9 down, with no pre-numbered rows.** Pre-numbered
   empty rows are something R3 has to tolerate in old workbooks, not something to keep producing.
   A list that stops at a fixed row leaves contributors with large datasets without it.
3. **The `readme` sheet states the package version and the vocabulary release.** A downloaded file
   outlives the page it came from. Without the two, nobody can tell which rules a filled-in
   workbook was prepared against.
4. **"Each version downloadable" means the site links the template for the version it documents.**
   The site is deployed from the default branch only. A permanent address for every earlier
   version is G12 and R13. Attaching each release's template to its GitHub release would need a
   change to the publish workflow, which is outside this feature, so it is not proposed here.
5. **Developers generate the template through the Python interface only.** The package has no
   command line yet. The checking command (R3) is where a command line first appears, and a
   command for the template can then be added to this specification as one more scenario.
6. **The documentation lists how the generated template differs from the last hand-maintained
   one.** R2 asks for differences from older templates to be noted. Reading older templates is R3,
   but contributors switching to the generated template need to know what moved now. The list is
   written once, against the template the GHFDB portal distributes today.
7. **Generation is reproducible.** The same version always produces the same content, so the
   published template and a developer's copy can be compared, and a change to the template is
   always a change to the field schema or the vocabulary release.
8. **A field fact the template needs but the field schema lacks is FS-001's to add.** The
   description rows include domain and quality relevance, which the field reference issue does
   not name. The template never supplies them itself, so the field schema stays the single
   description of every field.

## Open risks

- FS-001 is being specified in parallel. If its field schema does not carry domain, quality
  relevance and name for every field, rows 3, 4 and 5 of the template cannot be generated until
  it does.
- Very long vocabularies cannot be written into a choice list inline. The choice list then reads
  its terms from the `controlled vocabulary` sheet, which the layout already provides.

## Made while planning

### D-9 — A choice list goes on every field with a fixed list of allowed values

The specification offers a choice list on every vocabulary field and none on any other
(FR-004, FR-005). The field reference (FS-001, D-5) gives P9 and C9 a fixed set of values from
Fuchs et al. (2023) and no vocabulary. **Chosen:** the line falls between a field with a fixed
list of allowed values and one without, so P9 and C9 get a choice list of their fixed set, as
the hand-maintained template gives them. C20 has no list in the field reference and gets none,
and the differences page shows that it lost one. Read literally, FR-005 and AS 1.5 say otherwise
for P9 and C9, and the design review asked for this reading to be put to the maintainer. The
instruction for this build is to record such a change and carry on, so it is recorded here and
named when the pull request is handed over for review.

**ADR:** none — a reading of FS-001 for two fields, which nothing else inherits

### D-10 — openpyxl becomes a runtime dependency

**Chosen:** openpyxl writes the workbook. It writes list validations that reference another
sheet and accept any value, is typed, and is the reader checking (R3) will need. XlsxWriter only
writes, and hand-written SpreadsheetML would be several hundred lines. `ghfdb.fields` still
needs only the standard library, because the template is a module of its own.

**ADR:** pending — decided at convergence

### D-11 — Every choice list reads its terms from the `controlled vocabulary` sheet

**Chosen:** one mechanism for every field. An inline list is limited to 255 characters, which
C46 alone exceeds, and referencing the sheet makes the list and the sheet agree by construction.
The columns of `controlled vocabulary` sit under the same letters as on `data list`, which the
hand-maintained template intended and lost from P10 onwards.

**ADR:** none — a layout choice inside the template

### D-12 — "Identical content" means sheets, cells and choice lists

openpyxl stamps the time in the file's document properties and archive entries. **Chosen:** two
generations are compared by what a contributor or the portal reads: sheet names, cell values and
choice lists. Making the bytes identical would mean rewriting the archive after openpyxl saves
it, for a guarantee no reader of the workbook can see.

**ADR:** none — local to this feature

### D-13 — The differences page is computed from the two workbooks

**Chosen:** the documentation build compares the generated template with the stored
hand-maintained one (`tests/sources/upload-template.xlsx`) and renders the differences. Written
by hand, the list would type some sixty vocabulary terms into a page and could be wrong on the
day it merged. The hand-maintained `controlled vocabulary` columns are matched to fields by their
label, and the one label that names no field, "TC averaging method", is mapped to C48.

**ADR:** none — local to this feature

### D-14 — `-` stands for "none" in every description row

**Chosen:** the marker the hand-maintained template uses, so the portal's import reads what it
expects. A field with allowed values shows `-` in the range row: its values are its choice list.

**ADR:** none — follows the hand-maintained template

## Made at the design review

### D-15 — Refusing to replace a file is the standard library's `FileExistsError`

**Chosen:** `write` opens the path exclusively and lets openpyxl save into the open file, so the
refusal is the operating system's, raised as `FileExistsError` with a message that names the path
and says how to replace it. A package-specific exception would add a name and catch nothing a
developer could not already catch.

**ADR:** none — local to this feature

### D-16 — The template page starts a contributor guide

The documentation standard allows one guide unless more are declared. **Chosen:** the template
page is the index of a second guide, for data assessors and contributors, declared in the Project
additions of `docs/contributing/standards/documentation.md`.

**ADR:** none — a documentation layout choice
