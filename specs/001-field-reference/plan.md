# Implementation Plan: A field reference for the upload template

**Branch**: `001-field-reference` | **Date**: 2026-11-03 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-field-reference/spec.md`, research in
[research.md](research.md), decisions in [decisions.md](decisions.md).

## Summary

A new subpackage, `ghfdb.fields`, ships the field schema as one hand-written Frictionless Table
Schema file and loads it into frozen dataclasses. Every fact in the file is written by hand with
its source. The file states no release or version of the vocabularies. Each of the 25 vocabulary
fields links to the permanent identifier of its concept scheme, and of its collection where there
is one, and holds no term. When the schema is loaded, each scheme's Turtle file is downloaded from
its identifier with `.ttl` added into a cache directory outside the repository, read with
`rdflib`, and each vocabulary field gets its allowed values from it. The complete Table Schema with
an `enum` on each field is built in memory. A Sphinx extension renders the field reference from
the loaded schema while the documentation builds, so the two cannot disagree.

## Technical Context

**Language/Version**: Python 3.12+

**Primary Dependencies**: `rdflib>=7` (reading the vocabularies). Development:
`frictionless>=5` (independent schema validation), `openpyxl>=3.1` (reading the template in
tests). Documentation: `sphinxcontrib-mermaid>=1`.

**Storage**: `ghfdb/fields/schema.json` (package data); the vocabulary files, downloaded into a
cache directory outside the repository, one per scheme; `tests/sources/upload-template.xlsx`
(the current template, repository only).

**Testing**: pytest, mirroring the source tree; coverage floors 90% project and 85% patch.

**Target Platform**: any platform Python runs on; the first load needs the network, and a cached file works offline.

**Project Type**: single Python package.

**Constraints**: mypy strict; deptry clean; ruff line length 88; documentation builds with
warnings as errors.

**Scale/Scope**: 70 fields, 15 concept schemes, about 200 concepts.

## Constitution Check

| Article | How this plan meets it |
|---|---|
| I Testing | Test-first per `docs/contributing/standards/testing.md`. No test asserts wording or layout. |
| II Simplicity | One JSON file, read with `json`. No second source format, no build step for the schema. |
| III Anti-Abstraction | No base classes. `FieldSchema` and `Vocabularies` are the classes with behaviour; the rest are frozen dataclasses. |
| IV Integration-First | The field definitions are tested the way a developer meets them: load, look up, read. The reading is tested on small test vocabularies and on the real published ones. |
| V Security & data-safety | No workbook is read. A file is downloaded over HTTPS from the scheme's identifier. The template copy in `tests/sources/` is opened read-only, formulas not evaluated (`data_only=True`). |
| VI Documentation | README, `CHANGELOG.md`, `CONTEXT.md` and the documentation change in the same pull request. |
| VII Dependency discipline | `rdflib` is a runtime dependency, because loading the field schema reads the vocabularies; the reason is stated in the pull request. |
| VIII Cohesion | Lookup and loading live on `FieldSchema`; reading the vocabularies and computing allowed values live on `Vocabularies`. |
| IX Every rule names its source | Every fact of every field carries its source; a test fails a fact without one. |
| X Rules, examples, code together | Not a validation rule or scoring change; no **Scheme changes** entry. |
| XI Vocabulary from the published vocabularies | Allowed values are read from the published vocabularies at load time and never written to a file; tests start with an empty cache, so they read the files as currently published and fail when the vocabularies change. |
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
ghfdb/fields/
├── __init__.py        # re-exports the public names
├── schema.py          # FieldSchema, Field
├── schema.json        # the field schema, written by hand
└── vocabularies.py    # VocabularyBinding, AllowedValue, Vocabularies, MissingSchemeError

docs/
├── extensions/field_reference.py
├── reference/
│   ├── index.md
│   ├── python-api.md
│   └── fields/
│       ├── index.md       # opening page: how to find a field, the index, where facts come from
│       ├── parent.md
│       ├── child.md
│       └── assessment.md
├── developer/field-definitions.md       # guide: loading and looking up the field definitions
└── contributing/vocabularies.md   # how the vocabularies are fetched

tests/
├── sources/upload-template.xlsx
├── test_fields/
│   ├── __init__.py
│   ├── test_schema.py
│   └── test_vocabularies.py
└── test_docs/
    ├── __init__.py
    └── test_extensions/
        ├── __init__.py
        └── test_field_reference.py
```

`tests/test_docs/test_extensions/test_field_reference.py` mirrors
`docs/extensions/field_reference.py`. pytest's `pythonpath` gains `docs`, so the test imports
`extensions.field_reference`.

## Design

### The field schema file

A Frictionless Table Schema (research.md, "Frictionless Table Schema shape"):

```json
{
  "missingValues": [""],
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
        "scheme": "https://w3id.org/ihfc-iugg/vocabularies/conductivity-methods",
        "collection": null,
        "termForm": "label"
      },
      "constraints": {},
      "sources": {
        "code": "upload-template", "columnName": "upload-template", "name": "upload-template",
        "meaning": "fuchs-2023-appendix-a", "type": "fuchs-2023-appendix-a",
        "unit": "upload-template", "obligation": "upload-template", "domain": "upload-template",
        "qualityRelevance": "upload-template", "vocabulary": "vocabularies",
        "termForm": "upload-template", "allowedValues": "vocabularies"
      }
    }
  ]
}
```

- **Field properties**, all present on every field, `null` or `[]` where they do not apply:
  `name` (field code), `columnName`, `earlierColumnNames` (D-2), `group` (`parent`, `child`,
  `assessment`), `title`, `description`, `type`, `decimalPlaces`, `unit`, `valueFormat` (C38, A3:
  `YYYY-MM`; `format` is a reserved Table Schema property and is never used), `obligation` (`M`, `R`, `O` or `null`, D-14), `domain` (`B`, `S`), `qualityRelevance`
  (`U-score`, `M-score`, `perturbation flags` or `null`, D-16), `constraints`, `vocabulary`,
  `allowedValues` (only the hand-written values of P9 and C9), `separator` (D-23), `guidance` (D-5, D-22), `sources`.
- **`constraints`** holds `minimum`/`maximum` from the template's range (D-17), `maxLength: 255`
  for `Char (255)` fields, `pattern` for a format, and `enum` for a single-valued field with
  allowed values (the vocabulary fields and P9, C9), which `FieldSchema.descriptor()` adds in
  memory and the file never holds. For C38, `pattern` accepts `YYYY-MM` or
  `[Unspecified]` (D-18).
- **`sources`** has exactly one key per fact, every field, each a source code: `upload-template`,
  `fuchs-2023-appendix-a`, `vocabularies`, or `decision:D-<n>`. A fact the field does not
  record (`unit: null`) still names where its absence comes from. The keys, one per `Field`
  attribute other than `sources`, are fixed by this table, which the source test iterates:

  | `Field` attribute | `sources` key |
  |---|---|
  | `code` | `code` |
  | `column_name`, `earlier_column_names` | `columnName`, `earlierColumnNames` |
  | `group` | `group` |
  | `name`, `meaning` | `name`, `meaning` |
  | `type`, `decimal_places`, `max_length` | `type`, `decimalPlaces`, `maxLength` |
  | `unit`, `value_format` | `unit`, `valueFormat` |
  | `obligation`, `domain`, `quality_relevance` | `obligation`, `domain`, `qualityRelevance` |
  | `minimum`, `maximum` | `range` |
  | `vocabulary` | `vocabulary` (the binding) and `termForm` |
  | `allowed_values` | `allowedValues` |
  | `separator`, `guidance` | `separator`, `guidance` |
- **Fixed allowed values** (P9, C9) are `{"term": "[Yes]", "uri": null, "label": "Yes",
  "notation": null}` and the field's `vocabulary` is `null`; their source is
  `fuchs-2023-appendix-a` (D-5).
- **The vocabulary binding is written by hand as permanent identifiers**: `scheme` (such as
  `https://w3id.org/ihfc-iugg/vocabularies/conductivity-methods`) and `collection` (such as
  `https://w3id.org/ihfc-iugg/vocabularies/heat-flow-corrections/insitu`, or `null`). A scheme or
  collection its published file does not define stops the load (FR-016). No release, version or
  DOI is stated (FR-007).
- **Allowed values of a vocabulary field** are the concepts of the scheme, or of the collection
  where the field links to one (C11: `…/heat-flow-corrections/insitu`, C12: `…/temperature`,
  C13–C19: `…/generic`), sorted by term ignoring case (D-21). The term is `[<notation>]` where
  `termForm` is `notation` and the concept has one, otherwise `[<English preferred label>]`
  (D-20).
- Fields are in field-code order: P1–P13, C1–C49, A1–A8.

### `ghfdb.fields.schema`

```python
@dataclass(frozen=True)
class VocabularyBinding:
    scheme: str                        # permanent identifier of the concept scheme
    collection: str | None             # permanent identifier of the collection, or None
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
    value_format: str | None
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
    data: Mapping[str, Any]            # the schema file as written, without allowed values
    fields: tuple[Field, ...]          # field-code order

    @classmethod
    def load(cls, path: Path | None = None,
             vocabularies: Vocabularies | None = None) -> FieldSchema: ...  # default: the packaged file
    def __getitem__(self, key: str) -> Field: ...   # field code or published column name
    def __iter__(self) -> Iterator[Field]: ...
    def __len__(self) -> int: ...
```

- `load()` reads the packaged file with `importlib.resources`, so it works from a wheel. It takes
  the vocabulary files from the cache, downloading them on first use, or from the `Vocabularies`
  it is given (FR-010).
- `descriptor()` builds the complete Table Schema in memory (FR-019).
- `__getitem__` raises `UnknownFieldError` whose message names the key asked for (US2 scenario 3).
- `ghfdb.fields` re-exports `FieldSchema`, `Field`, `AllowedValue`, `VocabularyBinding`,
  `Vocabularies`, `MissingSchemeError` and `UnknownFieldError`.

### `ghfdb.fields.vocabularies`

```python
class Vocabularies:
    """The vocabulary files a field schema points at, cached on disk."""
    def __init__(self, cache: Path | None = None) -> None: ...
    def allowed_values(self, binding: VocabularyBinding) -> tuple[AllowedValue, ...]: ...
        # raises MissingSchemeError(scheme or collection identifier) when the file lacks it
    def graph(self, scheme: str) -> Graph: ...     # downloads <scheme>.ttl when absent or old

class MissingSchemeError(LookupError):
    """Names the field code and the scheme or collection that is not defined."""
```

- Only the scheme files a field needs are read. A collection is found by its identifier in the scheme's file. The members
  of a `skos:OrderedCollection` keep the collection's order; every other list is sorted by term.
- The download is the scheme's identifier with `.ttl` added, through a `requests-cache`
  `CachedSession` (filesystem backend, `cache_control=True`, `expire_after=0`,
  `stale_if_error=True`, two retries on 502, 503 and 504). The server's `ETag`, `Last-Modified`
  and `Cache-Control` decide freshness, so an unchanged file costs a `304` and no fixed expiry
  hides a change. The cache is `$GHFDB_VOCABULARY_CACHE`, else `ghfdb/vocabularies` in the
  user's cache directory. `Vocabularies` takes a session, so tests use an in-memory one.
- `rdflib` is imported by this module, which `ghfdb.fields` imports.

### The vocabulary checks (FR-017)

The test session's cache starts empty (`tests/conftest.py`), so the tests load the shipped schema
against the files as currently published. One test checks that every scheme and collection the
schema links to is defined in its file. Small synthetic vocabularies under
`tests/test_fields/vocabularies/` cover the reading itself, including ordered collections, and a
fake site (a transport adapter on an in-memory cached session) stands in for the web to cover the
download, revalidation with the `ETag`, a changed file, an unreachable server and a failed or
non-Turtle download.

### The documentation

- `docs/conf.py` puts `docs` on `sys.path` and lists `extensions.field_reference`,
  `sphinx.ext.autodoc` and `sphinxcontrib.mermaid`.
- `docs/extensions/field_reference.py` connects to `source-read` and
  replaces a marker line in a page (`{field-index}`, `{field-entries} parent`) with Markdown
  generated from `FieldSchema.load()`. On `builder-inited` it writes the complete Table Schema,
  `FieldSchema.descriptor()`, into the
  documentation source as a download (`docs/reference/fields/ghfdb-field-schema.json`, listed in `.gitignore`), and the opening
  page links to it with `{download}`.
- **Each entry** is a section headed with the field code, column name and name, preceded by two
  MyST targets, `(field-<code>)=` and `(field-<column name>)=` (lower case), so an entry is
  reachable by either (FR-012). Under it, one table with a row per fact in the fixed order of
  FR-003 (field code, published column name, name, meaning, type, unit, obligation, domain,
  quality relevance, then range, format or allowed values), each with its source. A source that is
  a decision links to it in `decisions.md` on GitHub.
- **A vocabulary field's allowed values** follow the table: the concept scheme, the
  collection where there is one, then every term as written in a cell,
  each linked to its concept URI. A field with a separator says so (US1 scenario 6). A field with
  an earlier column name gives it (US1 scenario 5).
- **The opening page** (`reference/fields/index.md`) says what the reference is, gives the index
  (one row per field: code, column name, name, each linking to the entry) so any field is one step
  away (SC-004), explains where the facts and allowed values come from with a Mermaid diagram, and
  how the allowed values stay current with a second (FR-014), and links the schema download.
- **The Python API page** (`reference/python-api.md`) is `automodule` on `ghfdb.fields`.
- **The developer guide** (`developer/field-definitions.md`) is the task of loading the field
  definitions and looking a field up, linking to the API page and the field reference. The
  explanation of where facts come from stays on the field reference's opening page, where FR-014
  puts it.
- **`contributing/vocabularies.md`** explains where the files come from, how the cache is
  refreshed, and what to do when the tests report a change.
- `docs/index.md` gains a Reference section in its contents.

### Other files

- `CONTEXT.md`: field reference, assessment fields A1–A8, domain, quality relevance, field schema
  as built (FR-018), and field code extended to `A1`–`A8`.
- `README.md`: one paragraph and a three-line example of loading the field definitions, linking
  to the reference.
- `CHANGELOG.md`: under Unreleased → Added.
- `pyproject.toml`: the `rdflib` dependency, the development and documentation dependencies,
  `docs` in mypy's files and pytest's `pythonpath`, `types-openpyxl`.

## Complexity Tracking

| Choice | Why it is needed | Simpler alternative rejected because |
|---|---|---|
| Dependency `rdflib` | Parsing Turtle and SKOS by hand is a parser this repository would own | Parsing N-Triples with a regular expression handles one format, and every SKOS query would be hand-written |
| A Sphinx extension | The reference must never disagree with the schema (FR-013) | Committed generated pages need a second check that they are current, and can drift between runs |
