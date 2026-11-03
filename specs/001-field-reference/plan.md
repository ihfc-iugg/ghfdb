# Implementation Plan: A field reference for the upload template

**Branch**: `001-field-reference` | **Date**: 2026-11-03 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-field-reference/spec.md`, research in
[research.md](research.md), decisions in [decisions.md](decisions.md).

## Summary

A new subpackage, `ghfdb.fields`, ships the field schema as one Frictionless Table Schema file and
loads it into frozen dataclasses with the standard library. Every fact in the file is written by
hand with its source, except the allowed values of the 26 vocabulary fields and the stated
release, which only the step that adopts a vocabulary release writes. That step reads the
release's Turtle files with `rdflib`, an optional dependency, from a copy of the release kept in
the repository, and reports per field what changed. A Sphinx extension renders the field reference
from the loaded schema while the documentation builds, so the two cannot disagree.

## Technical Context

**Language/Version**: Python 3.12+

**Primary Dependencies**: none at runtime. Optional extra `vocabularies`: `rdflib>=7`. Development:
`frictionless>=5` (independent schema validation), `openpyxl>=3.1` (reading the template in
tests), `rdflib>=7`. Documentation: `sphinxcontrib-mermaid>=1`.

**Storage**: `src/ghfdb/fields/schema.json` (package data); `vocabularies/<version>/*.ttl` (the
stated release, repository only); `tests/sources/upload-template.xlsx` (the current template,
repository only).

**Testing**: pytest, mirroring the source tree; coverage floors 90% project and 85% patch.

**Target Platform**: any platform Python runs on; loading needs no network.

**Project Type**: single Python package.

**Constraints**: mypy strict; deptry clean; ruff line length 88; documentation builds with
warnings as errors.

**Scale/Scope**: 70 fields, 15 concept schemes, about 200 concepts.

## Constitution Check

| Article | How this plan meets it |
|---|---|
| I Testing | Test-first per `docs/contributing/standards/testing.md`. No test asserts wording or layout. |
| II Simplicity | One JSON file, read with `json`. No second source format, no build step for the schema. |
| III Anti-Abstraction | No base classes. `FieldSchema`, `ReleaseFiles` and `ReleaseMove` are the classes with behaviour; the rest are frozen dataclasses. |
| IV Integration-First | The field definitions are tested the way a developer meets them: load, look up, read. The release step is tested by running it on a test release. |
| V Security & data-safety | No workbook is read. The release step reads only files the maintainer names. The template copy in `tests/sources/` is opened read-only, formulas not evaluated (`data_only=True`). |
| VI Documentation | README, `CHANGELOG.md`, `CONTEXT.md` and the documentation change in the same pull request. |
| VII Dependency discipline | No runtime dependency. `rdflib` is an optional extra for the one step that needs it; the reason is stated in the pull request. |
| VIII Cohesion | Lookup and loading live on `FieldSchema`; reading a release and computing allowed values live on `ReleaseFiles`; adopting a release lives on `ReleaseMove`. |
| IX Every rule names its source | Every fact of every field carries its source; a test fails a fact without one. |
| X Rules, examples, code together | Not a validation rule or scoring change; no **Scheme changes** entry. |
| XI Vocabulary from the release | Allowed values are written only by `ReleaseMove`; a test regenerates them from the stored release and fails on any difference. |
| XIII Whole columns | No rows are processed. |
| XIV Compatibility | New public API `ghfdb.fields`, recorded in `CHANGELOG.md`. |
| XV Stack | uv, hatchling, pytest, pre-commit, mypy, Sphinx with MyST. pandas is not needed: no tabular data is processed. |

## Project Structure

### Documentation (this feature)

```text
specs/001-field-reference/
├── spec.md
├── decisions.md
├── research.md
├── plan.md
└── tasks.md
```

### Source code

```text
src/ghfdb/fields/
├── __init__.py        # re-exports the public names
├── schema.py          # FieldSchema, Field, AllowedValue, VocabularyBinding, VocabularyRelease
├── schema.json        # the field schema
└── release.py         # ReleaseFiles, ReleaseMove, FieldChange, command-line entry point

vocabularies/2026.1/   # the 15 Turtle files of v2026.1 and LICENSE-CC-BY-4.0

docs/
├── _ext/field_reference.py
├── reference/
│   ├── index.md
│   ├── python-api.md
│   └── fields/
│       ├── index.md       # opening page: how to find a field, the index, where facts come from
│       ├── parent.md
│       ├── child.md
│       └── assessment.md
└── contributing/vocabulary-release.md   # adopting a newer vocabulary release

tests/
├── sources/upload-template.xlsx
├── test_fields/
│   ├── __init__.py
│   ├── test_schema.py
│   └── test_release.py
└── test_docs/
    ├── __init__.py
    └── test_field_reference.py
```

`tests/test_docs/` mirrors `docs/_ext/field_reference.py`, which is not under `src/`. It is
declared under `[tool.forge.conformance] non-mirror-paths` in `pyproject.toml`.

## Design

### The field schema file

A Frictionless Table Schema (research.md, "Frictionless Table Schema shape"):

```json
{
  "missingValues": [""],
  "vocabularyRelease": {"version": "2026.1", "doi": "10.5880/fidgeo.2026.065"},
  "fields": [
    {
      "name": "C43",
      "columnName": "tc_method",
      "group": "child",
      "title": "Thermal conductivity method",
      "description": "…",
      "type": "string",
      "unit": null,
      "obligation": "M",
      "domain": ["B", "S"],
      "qualityRelevance": "M-score",
      "vocabulary": {
        "scheme": "https://portal.heatflow.world/vocabularies/conductivity-methods",
        "collection": null,
        "termForm": "label"
      },
      "allowedValues": [
        {"term": "[Lab - point source]", "uri": "…/pointSource", "label": "Lab - point source", "notation": null}
      ],
      "constraints": {"enum": ["[Lab - point source]", "…"]},
      "sources": {
        "code": "upload-template", "columnName": "upload-template", "name": "upload-template",
        "meaning": "fuchs-2023-appendix-a", "type": "fuchs-2023-appendix-a",
        "unit": "upload-template", "obligation": "upload-template", "domain": "upload-template",
        "qualityRelevance": "upload-template", "vocabulary": "vocabulary-release",
        "termForm": "upload-template", "allowedValues": "vocabulary-release"
      }
    }
  ]
}
```

- **Field properties**, all present on every field, `null` or `[]` where they do not apply:
  `name` (field code), `columnName`, `earlierColumnNames` (D-2), `group` (`parent`, `child`,
  `assessment`), `title`, `description`, `type`, `decimalPlaces`, `unit`, `format` (C38, A3:
  `YYYY-MM`), `obligation` (`M`, `R`, `O` or `null`, D-14), `domain` (`B`, `S`), `qualityRelevance`
  (`U-score`, `M-score`, `perturbation flags` or `null`, D-16), `constraints`, `vocabulary`,
  `allowedValues`, `separator` (D-23), `guidance` (D-5, D-22), `sources`.
- **`constraints`** holds `minimum`/`maximum` from the template's range (D-17), `maxLength: 255`
  for `Char (255)` fields, `pattern` for a format, and `enum` for a single-valued field with
  allowed values (the vocabulary fields and P9, C9). For C38, `pattern` accepts `YYYY-MM` or
  `[Unspecified]` (D-18).
- **`sources`** has one key per fact the field records, each a source code: `upload-template`,
  `fuchs-2023-appendix-a`, `vocabulary-release`, or `decision:D-<n>`. A fact the field does not
  record (`unit: null`) still names where its absence comes from.
- **Fixed allowed values** (P9, C9) are `{"term": "[Yes]", "uri": null, "label": "Yes",
  "notation": null}` and the field's `vocabulary` is `null`; their source is
  `fuchs-2023-appendix-a` (D-5).
- **Allowed values of a vocabulary field** are the concepts of the scheme, or of the collection
  where the field names one (C11: `…/heat-flow-corrections/insitu`, C12: `…/temperature`,
  C13–C19: `…/generic`), sorted by term ignoring case (D-21). The term is `[<notation>]` where
  `termForm` is `notation` and the concept has one, otherwise `[<English preferred label>]`
  (D-20).
- Fields are in field-code order: P1–P13, C1–C49, A1–A8.

### `ghfdb.fields.schema`

```python
@dataclass(frozen=True)
class VocabularyRelease:
    version: str
    doi: str

@dataclass(frozen=True)
class VocabularyBinding:
    scheme: str
    collection: str | None
    term_form: Literal["label", "notation"]

@dataclass(frozen=True)
class AllowedValue:
    term: str
    label: str
    uri: str | None
    notation: str | None

@dataclass(frozen=True)
class Field:
    code: str
    column_name: str
    earlier_column_names: tuple[str, ...]
    group: Literal["parent", "child", "assessment"]
    name: str
    meaning: str
    type: str
    decimal_places: int | None
    unit: str | None
    format: str | None
    obligation: Literal["M", "R", "O"] | None
    domain: tuple[str, ...]
    quality_relevance: str | None
    minimum: float | None
    maximum: float | None
    max_length: int | None
    vocabulary: VocabularyBinding | None
    allowed_values: tuple[AllowedValue, ...]
    separator: str | None
    guidance: str | None
    sources: Mapping[str, str]

class UnknownFieldError(KeyError):
    """Raised for a field code or published column name the schema does not hold."""

class FieldSchema:
    path: Path                         # the JSON file it was read from
    release: VocabularyRelease
    fields: tuple[Field, ...]          # field-code order

    @classmethod
    def load(cls, path: Path | None = None) -> FieldSchema: ...  # default: the packaged file
    def __getitem__(self, key: str) -> Field: ...   # field code or published column name
    def __iter__(self) -> Iterator[Field]: ...
    def __len__(self) -> int: ...
```

- `load()` reads the packaged file with `importlib.resources`, so it works from a wheel with no
  network (FR-010).
- `__getitem__` raises `UnknownFieldError` whose message names the key asked for (US2 scenario 3).
- `ghfdb.fields` re-exports `FieldSchema`, `Field`, `AllowedValue`, `VocabularyBinding`,
  `VocabularyRelease` and `UnknownFieldError`.

### `ghfdb.fields.release`

```python
class ReleaseFiles:
    """One vocabulary release, read from the directory holding its Turtle files."""
    def __init__(self, directory: Path, version: str) -> None: ...
    @property
    def release(self) -> VocabularyRelease: ...       # DOI from dcterms:isPartOf, the same on every scheme
    def allowed_values(self, binding: VocabularyBinding) -> tuple[AllowedValue, ...]: ...
        # raises MissingSchemeError(scheme or collection URI) when the release lacks it

@dataclass(frozen=True)
class FieldChange:
    code: str
    added: tuple[AllowedValue, ...]
    removed: tuple[AllowedValue, ...]
    relabelled: tuple[tuple[AllowedValue, AllowedValue], ...]   # same URI, different term

class ReleaseMove:
    """Regenerate the allowed values of a field schema file from a release."""
    def __init__(self, schema_path: Path, release: ReleaseFiles) -> None: ...
    def changes(self) -> tuple[FieldChange, ...]: ...   # one per vocabulary field, in field-code order
    def apply(self) -> tuple[FieldChange, ...]: ...     # writes the file; nothing written on failure

class MissingSchemeError(LookupError):
    """Names the field code and the scheme or collection the release lacks."""

def main(argv: Sequence[str] | None = None) -> int:
    """python -m ghfdb.fields.release <version> <directory> [--schema PATH] [--changelog PATH]"""
```

- `ReleaseMove.apply` edits only `allowedValues`, `constraints.enum` of vocabulary fields, and
  `vocabularyRelease`, on the parsed JSON, and writes it back with the same indentation, so every
  other byte of the file is unchanged (FR-015, SC-005). Every field is resolved before anything is
  written, so a missing scheme leaves the file untouched (FR-016).
- `main` prints one line per vocabulary field, `C43: unchanged` or the concepts added, removed
  and relabelled, and adds a line under `## [Unreleased]` → `### Changed` in the changelog naming
  the old and new release (US3 scenario 6). It exits 1 with the field and scheme on a missing
  scheme.
- `rdflib` is imported inside this module only. Importing `ghfdb.fields` never imports it.

### The drift check (FR-017)

A test builds `ReleaseFiles(vocabularies/<stated version>/, version)` and compares its
`allowed_values` with every vocabulary field's in the shipped schema, failing with the codes of the
fields that differ. A hand edit to an allowed value, or a release directory that does not match
the stated release, fails it.

### The documentation

- `docs/_ext/field_reference.py`, registered in `docs/conf.py`, connects to `source-read` and
  replaces a marker line in a page (`{field-index}`, `{field-entries} parent`) with Markdown
  generated from `FieldSchema.load()`. On `builder-inited` it copies `schema.json` into the
  documentation source as a download (`ghfdb-field-schema.json`, git-ignored), and the opening
  page links to it with `{download}`.
- **Each entry** is a section headed with the field code, column name and name, preceded by two
  MyST targets, `(field-<code>)=` and `(field-<column name>)=` (lower case), so an entry is
  reachable by either (FR-012). Under it, one table with a row per fact in the fixed order of
  FR-003 (field code, published column name, name, meaning, type, unit, obligation, domain,
  quality relevance, then range, format or allowed values), each with its source. A source that is
  a decision links to it in `decisions.md` on GitHub.
- **A vocabulary field's allowed values** follow the table: the concept scheme (linked), the
  collection where there is one, the release and its DOI, then every term as written in a cell,
  each linked to its concept URI. A field with a separator says so (US1 scenario 6). A field with
  an earlier column name gives it (US1 scenario 5).
- **The opening page** (`reference/fields/index.md`) says what the reference is, gives the index
  (one row per field: code, column name, name, each linking to the entry) so any field is one step
  away (SC-004), explains where the facts and allowed values come from with a Mermaid diagram, and
  how a newer release is adopted with a second (FR-014), and links the schema download.
- **The Python API page** (`reference/python-api.md`) is `automodule` on `ghfdb.fields` and
  `ghfdb.fields.release`.
- **`contributing/vocabulary-release.md`** is the maintainer's how-to: download the release's
  Turtle files into `vocabularies/<version>/`, run the step, read the report, remove the old
  directory, open the pull request.
- `docs/index.md` gains a Reference section in its contents.

### Other files

- `CONTEXT.md`: field reference, assessment fields A1–A8, domain, quality relevance, field schema
  as built (FR-018), and field code extended to `A1`–`A8`.
- `README.md`: one paragraph and a three-line example of loading the field definitions, linking
  to the reference.
- `CHANGELOG.md`: under Unreleased → Added.
- `pyproject.toml`: the optional extra, the development and documentation dependencies,
  `/vocabularies` in the sdist, `docs/_ext` in mypy's files, the conformance declaration.

## Complexity Tracking

| Choice | Why it is needed | Simpler alternative rejected because |
|---|---|---|
| Optional dependency `rdflib` | Parsing Turtle and SKOS by hand is a parser this repository would own | Parsing N-Triples with a regular expression handles one format, and every SKOS query would be hand-written |
| A Sphinx extension | The reference must never disagree with the schema (FR-013) | Committed generated pages need a second check that they are current, and can drift between runs |
