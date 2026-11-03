# Implementation Plan: A generated upload template

**Branch**: `002-upload-template` | **Spec**: [spec.md](spec.md) | **Research**: [research.md](research.md)

## Summary

A new module, `ghfdb.template`, builds the upload template from the field schema with openpyxl:
the `readme`, `data list` and `controlled vocabulary` sheets, the description rows, and a choice
list that references `controlled vocabulary` on every field with allowed values. A developer
writes it to a path, which is never overwritten unless asked. A documentation extension writes
the same workbook during the build, links it from a new page about the template, and renders
the differences from the hand-maintained template by comparing the two workbooks.

## Technical Context

- **Language**: Python 3.12+, managed with uv, built with hatchling.
- **New runtime dependency**: `openpyxl>=3.1` (research.md, "Writing the workbook"). It moves
  from the development group to `[project] dependencies`. `types-openpyxl` stays a development
  dependency.
- **Reads**: `ghfdb.fields.FieldSchema` (FS-001). No field fact is written into the new code.
- **Documentation**: Sphinx with MyST, built with `-W`. A second extension beside
  `docs/extensions/field_reference.py`.
- **Tests**: pytest. Workbooks are written to `tmp_path` and read back with openpyxl.
- **Checks**: mypy strict, deptry, pre-commit (ruff, line length 88), coverage floors 90 %
  project and 85 % patch.

## Constitution Check

| Article | How the plan meets it |
|---|---|
| II Simplicity | One class and two small exceptions. One validation mechanism for every list. |
| III Anti-abstraction | No base class. The comparison class lives only in the documentation extension, its one user. |
| IV Integration-first | Tests write a real workbook and read it back, as a contributor or the portal would. |
| V Data safety | Generation writes only the path it is given and reads no workbook. The comparison reads the stored hand-maintained template with openpyxl, which evaluates no formula. |
| VI Documentation | A page for contributors, a developer guide page, a Python API entry, README and CHANGELOG, in this pull request. |
| VII Dependencies | openpyxl becomes a runtime dependency, reason in research.md. deptry passes. |
| VIII Cohesion | `UploadTemplate` holds every step of building the workbook. `TemplateChanges` holds every comparison. |
| IX Sources | No rule is added. Every value the template shows is one the field schema sources. |
| XI Vocabulary | Every term comes from `AllowedValue.term`. The differences page is computed, so no term is typed into a page. |
| XII Report, never modify | The hand-maintained template is read, never written. |
| XIII Whole columns | Not a check or a score. The generator writes one column per field, and the comparison iterates fields and rows of a 70 × 8 grid, which is not data. |
| Mermaid | The template page shows the generation as a flowchart. |

## Project Structure

### Documentation (this feature)

```text
specs/002-upload-template/
├── spec.md
├── decisions.md
├── research.md
├── plan.md
└── tasks.md
```

### Source code

```text
src/ghfdb/template.py                      # UploadTemplate, TemplateError
docs/extensions/upload_template.py         # writes the workbook, the download link, TemplateChanges
docs/upload-template/index.md              # the template page, for contributors
docs/developer/upload-template.md          # generating the template from Python
docs/reference/python-api.md               # gains the ghfdb.template entry
docs/index.md                              # links the template page from the home page
docs/conf.py                               # registers the extension
tests/test_template.py
tests/test_docs/test_extensions/test_upload_template.py
pyproject.toml, uv.lock, .gitignore, README.md, CHANGELOG.md
```

## Design

### `ghfdb.template`

```python
class TemplateError(ValueError):
    """A field the template cannot be written for, named in the message."""

class UploadTemplate:
    def __init__(self, schema: FieldSchema | None = None) -> None: ...
    def workbook(self) -> Workbook: ...
    def write(self, path: Path, replace: bool = False) -> None: ...
```

- `schema` defaults to `FieldSchema.load()`. The package version is `ghfdb.__version__`, which
  already exists.
- `workbook()` builds the three sheets in the order `readme`, `data list`,
  `controlled vocabulary`, and nothing else (openpyxl's default sheet is renamed, not left).
- **`data list`**: A1 `ID`. Field `i` (from 0, schema order) sits in column `i + 2`. Row 1 its
  code. Column A rows 2–8 hold the row labels `Obligation`, `Domain`, `Quality Relevance`,
  `Name`, `Short Name`, `Unit`, `Allowed range of values`, as the hand-maintained template has
  them (SC-004). Rows 2–8 under a field hold the values in research.md, "Description rows", all
  as strings, `-` for none. Row 1 bold, panes frozen at `B9`. Nothing from row 9 down.
- **Range formatting**: `minimum` and `maximum` both set → each formatted with a thousands
  separator and `decimal_places` digits (`0` when `decimal_places` is None), joined by
  `" – "` (space, en dash, space). Otherwise `value_format` when set. Otherwise `-`. A field with
  allowed values always shows `-`.
- **`controlled vocabulary`**: A1 `Field code`, A2 `Name`. For each field with allowed values, in
  the same column letter as on `data list`: row 1 the code, row 2 the name, from row 3 each
  `AllowedValue.term` in schema order.
- **Choice lists**: for each field with allowed values, one `DataValidation(type="list",
  formula1="'controlled vocabulary'!$X$3:$X$<2 + n>", allow_blank=True,
  showErrorMessage=False)` added to `data list`, its range `X9:X1048576`. A field with no allowed
  values gets none.
- **Failure**: a field whose `vocabulary` is set but whose `allowed_values` is empty raises
  `TemplateError` naming the field code, from `workbook()`. (The schema loader already fails on a
  file that cannot be read, and `FieldSchema.load()` is called in `__init__`, so that failure is
  raised with the file named.)
- **`readme`**: column A, one line per row: what the workbook is, the package version, the
  vocabulary release version and its DOI as `https://doi.org/<doi>`, the field reference URL
  `https://ihfc-iugg.github.io/ghfdb/reference/fields/index.html`, and how to fill it in (data
  from row 9 on `data list`, choice lists offer the allowed terms and accept any value).
  The version and release lines are computed, the rest is fixed wording and untested. It says
  nothing about checking, which arrives with R3.
- **`write(path, replace=False)`**: builds the workbook first, then opens `path` with mode `"xb"`,
  or `"wb"` when `replace` is true, and saves the workbook into the open file. A
  `FileExistsError` from `open` is re-raised as `FileExistsError` with a message naming the path
  and saying to pass `replace=True`. Nothing is written and the existing file is untouched.
- `ghfdb.template` is not re-exported from `ghfdb/__init__.py`. It is imported as
  `from ghfdb.template import UploadTemplate`.

### `docs/extensions/upload_template.py`

Mirrors `field_reference.py`.

- `DOWNLOAD_MARKER = re.compile(r"^\{upload-template-download\}$", re.MULTILINE)` and
  `CHANGES_MARKER = re.compile(r"^\{upload-template-changes\}$", re.MULTILINE)`.
- `HAND_MAINTAINED = <repository root>/tests/sources/upload-template.xlsx`, found from this
  file's location (`Path(__file__).parents[2]`).
- `template_name(version) -> str`: `ghfdb-upload-template-<version>.xlsx`.
- `write_template(template: UploadTemplate, source_directory: Path) -> Path`: writes into
  `source_directory / "upload-template" / template_name(...)` with `replace=True`, returns the
  path. Called from `builder-inited`. An exception propagates and fails the build (FR-008).
- `source_read`: on a page holding either marker, the download marker becomes
  `` {download}`<name> <name>` `` and the changes marker becomes `TemplateChanges(previous,
  generated).markdown()`, where `previous` is the hand-maintained workbook and `generated` is
  `UploadTemplate().workbook()`.
- `TemplateChanges(previous: Workbook, generated: Workbook)`, with these methods, each returning
  data, and `markdown()` rendering them under `###` headings, `None.` under a heading with nothing
  in it:
  - `columns()` → codes added, codes removed, and whether the common codes changed order, from
    row 1 of `data list` (column A excluded).
  - `description_rows()` → `(code, row label, previous, generated)` for every field in both and
    every row 2–8 whose values differ once whitespace (including non-breaking spaces) is collapsed
    and stripped, and `None` read as empty. Numbers are compared as `str(value)`.
  - `choice_lists()` → per field present in both: `(code, terms added, terms removed)`, plus the
    codes that gained a list and the codes that lost one. Previous terms: the hand-maintained
    `controlled vocabulary` column whose row 1 label, whitespace-collapsed and compared without
    case, equals the field's name on `data list` row 5. `PREVIOUS_LABELS = {"TC averaging method":
    "C48"}` maps the one label that equals no name (research.md). A previous column that holds
    terms and matches neither raises `ValueError` naming its label, so an edit to the stored file
    cannot silently shorten the list. Generated terms: the generated sheet's column for the code,
    from row 3.
  - Markdown cells are escaped as `FieldReference.cell` does; reuse it by import, not by copy.
- `setup` connects `builder-inited` and `source-read`, parallel safe.
- `.gitignore`: `docs/upload-template/*.xlsx`.

### Documentation pages

- `docs/upload-template/index.md`, in the home page's toctree under a new caption "Contributing
  data", placed first. It says what the template is and links the download (the marker), then
  opens by saying who it is for (a data assessor or contributor filling in the template), then
  the three sheets and the description rows, then "Changes from the hand-maintained template"
  holding the changes marker, and closes with the explanation: the choice lists offer the allowed
  terms and accept any value, the readme names the version and release, and the template is
  generated from the field reference, with a Mermaid flowchart: field schema and vocabulary
  release → `UploadTemplate` → documentation build → download. Home page → this page → download
  is two links (SC-005).
- `docs/contributing/standards/documentation.md`, Project additions: a Guides table with two
  rows, the developer guide (`developer/`, a developer using ghfdb from Python) and the
  contributor guide (`upload-template/`, a data assessor or contributor filling in the upload
  template), as its section 4 requires of a second guide.
- `docs/developer/upload-template.md`, added to the "Developer guide" toctree in
  `docs/index.md`: generate the template, choose a path, replace an existing file, read the
  version and release a template came from.
- `docs/reference/python-api.md`: a section "Upload template" with `automodule:: ghfdb.template`.
- README: a line under the documentation links pointing at the template page. CHANGELOG: `Added`
  lines for the template, the download and the developer interface, and `Changed` for openpyxl
  becoming a runtime dependency.

## Tests

- `tests/test_template.py`, against the packaged schema unless a test needs a small one (built by
  `dataclasses.replace` on loaded fields, never by typing terms):
  - sheet names and order; row 1 of `data list` is `ID` plus every code in schema order;
  - every description cell equals the value computed from its field (a test-local function from
    the field to the seven expected strings would restate the generator; instead assert per row
    against the field attribute it comes from, and the `-` marker for every field that lacks it);
  - range: one test each for a min/max field, a value-format field, an allowed-values field, a
    field with neither;
  - choice lists: the set of columns with a validation equals the set of fields with allowed
    values; each validation's range starts at row 9 and ends at row 1,048,576; its formula's range
    on `controlled vocabulary` holds exactly the field's terms; `showErrorMessage` is false;
  - the readme states `ghfdb.__version__` and the schema's release version and DOI;
  - `TemplateError` names the field for a vocabulary field with no allowed values;
  - layout against `tests/sources/upload-template.xlsx`: sheet names, A1, A2–A8, first empty
    row (SC-004);
  - `write`: writes to a new path; refuses an existing one with `FileExistsError` and leaves its
    bytes unchanged; replaces with `replace=True`; two generations have identical content
    (sheets, cell values, validations).
- The comparison of two workbook files lives once, as the fixture `workbook_content` in
  `tests/conftest.py`, returning a function from a path to the sheets, their cell values and their
  validations. Both test modules use it.
- `tests/test_docs/test_extensions/test_upload_template.py`:
  - `write_template` writes the versioned file under `upload-template/`, and its content is
    identical to `UploadTemplate().write(...)` to another path (SC-006);
  - `write_template` propagates a `TemplateError`;
  - the markers are replaced, and a page without them is untouched;
  - `TemplateChanges` on two small workbooks built in the test: an added code, a removed code, a
    reorder, a changed description cell, whitespace-only differences ignored, a term added and
    removed, a list gained and lost, `None.` sections;
  - `TemplateChanges` on the real pair finds C46's `Short Name` change and C20's lost list
    (values read from the two files, so the test holds whatever the wording);
  - a previous column with terms whose label matches no field raises `ValueError`.

## Complexity Tracking

None. One new runtime dependency, stated above.
