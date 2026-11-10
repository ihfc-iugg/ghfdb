# Implementation Plan: A field reference for the upload template

**Branch**: `001-field-reference` | **Date**: 2026-11-03 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-field-reference/spec.md`, research in
[research.md](research.md), decisions in [decisions.md](decisions.md).

## Summary

A new subpackage, `ghfdb.fields`, ships the field schema as one hand-written Frictionless Table
Schema file and loads it with Frictionless into a `frictionless.Schema`. Every fact in the file is written by hand with
its source. The file states no release or version of the vocabularies. Each of the 25 vocabulary
fields links to the permanent identifier of its concept scheme, and of its collection where there
is one, and holds no term. When the schema is loaded, each scheme's Turtle file is downloaded from
its identifier with `.ttl` added into a cache directory outside the repository, read with
`rdflib`, and each vocabulary field gets its allowed values from it. The loaded schema has an
`enum` on each field that has allowed values, in memory only. A Sphinx extension renders the field
reference from the loaded schema with Jinja2 templates while the documentation builds, so the two
cannot disagree.

## Technical Context

**Language/Version**: Python 3.12+

**Primary Dependencies**: `frictionless>=5` (reading and validating the schema), `rdflib>=7`
(reading the vocabularies), `requests` and `requests-cache` (downloading them), `platformdirs`
(the cache directory). Development: `openpyxl>=3.1` (reading the template in tests), `responses`
(a stand-in for the web). Documentation: `jinja2>=3.1` (the field reference templates),
`sphinxcontrib-mermaid>=1`.

**Storage**: `ghfdb/fields/schema.json` (package data); the vocabulary files, downloaded into a
cache directory outside the repository, one per scheme; `tests/sources/upload-template.xlsx`
(the current template, repository only).

**Testing**: pytest, mirroring the source tree; coverage floors 90% project and 85% patch.

**Target Platform**: any platform Python runs on; the first load needs the network, and a cached file works offline.

**Project Type**: single Python package.

**Constraints**: mypy strict; deptry clean; ruff line length 88; documentation builds with
warnings as errors.

**Scale/Scope**: 74 fields, 17 concept schemes, about 650 concepts.

## Constitution Check

| Article | How this plan meets it |
|---|---|
| I Testing | Test-first per `docs/contributing/standards/testing.md`. No test asserts wording or layout. |
| II Simplicity | One JSON file, read by Frictionless. No second source format, no build step for the schema, and no class restating Frictionless's own. |
| III Anti-Abstraction | No base classes and no wrapper around the Frictionless schema. `Vocabularies` is the class with behaviour; the functions that work on a `frictionless.Schema` are module-level because the type is not ours to extend. |
| IV Integration-First | The field definitions are tested the way a developer meets them: load, look up, read. The reading is tested on small test vocabularies and on the real published ones. |
| V Security & data-safety | No workbook is read. A file is downloaded over HTTPS from the scheme's identifier. The template copy in `tests/sources/` is opened read-only, formulas not evaluated (`data_only=True`). |
| VI Documentation | README, `CHANGELOG.md`, `CONTEXT.md` and the documentation change in the same pull request. |
| VII Dependency discipline | `frictionless` reads the schema, `rdflib` reads the vocabularies, and `requests-cache` and `platformdirs` download and place them, each in place of code this repository would otherwise own. deptry passes. |
| VIII Cohesion | Reading the vocabularies and computing allowed values live on `Vocabularies`. The three functions that work on a `frictionless.Schema` (load, allowed values of a field, find by column name) are standalone because Frictionless's classes are not ours. |
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
├── schema.py          # load_schema, allowed_values, field_for_column
├── schema.json        # the field schema, written by hand
└── vocabularies.py    # AllowedValue, Vocabularies, caching_session, MissingSchemeError

docs/
├── extensions/
│   ├── field_reference.py
│   └── templates/field_reference.md.jinja
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
├── example_site.py       # the example site that serves the test vocabularies
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
  allowed values (the vocabulary fields and P9, C9), which `load_schema()` adds in
  memory and the file never holds. For C38, `pattern` accepts `YYYY-MM` or
  `[Unspecified]` (D-18).
- **`sources`** has exactly one key per fact, every field, each a source code: `upload-template`,
  `fuchs-2023-appendix-a`, `vocabularies`, or `decision:D-<n>`. A fact the field does not
  record (`unit: null`) still names where its absence comes from. The keys, one per property of
  the field other than `sources`, are fixed by this table, which the source test iterates:

  | Property | `sources` key |
  |---|---|
  | `name` (the field code) | `code` |
  | `columnName`, `earlierColumnNames` | `columnName`, `earlierColumnNames` |
  | `group` | `group` |
  | `title`, `description` | `name`, `meaning` |
  | `type`, `decimalPlaces`, `constraints.maxLength` | `type`, `decimalPlaces`, `maxLength` |
  | `unit`, `valueFormat` | `unit`, `valueFormat` |
  | `obligation`, `domain`, `qualityRelevance` | `obligation`, `domain`, `qualityRelevance` |
  | `constraints.minimum`, `constraints.maximum` | `range` |
  | `vocabulary` | `vocabulary` (the binding) and `termForm` |
  | `allowedValues`, `constraints.enum` | `allowedValues` |
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
- Fields are in the order of the template's columns: P1–P13, C1–C38, C50–C53, C39–C49, A1–A8.

### `ghfdb.fields.schema`

The loaded schema is a `frictionless.Schema`. Its fields are Frictionless fields: `name` is the
field code, `title` the name, `description` the meaning, `type`, and `constraints` hold the range,
length, pattern and `enum`. Every other fact is in the field's `custom` dictionary under the key
the file gives it (`columnName`, `earlierColumnNames`, `group`, `decimalPlaces`, `unit`,
`valueFormat`, `obligation`, `domain`, `qualityRelevance`, `vocabulary`, `separator`, `guidance`,
`sources`). The vocabulary object is read as it is written in the file: `scheme`, `collection` and
`termForm`.

```python
@dataclass(frozen=True)
class AllowedValue:
    term: str
    label: str
    uri: str | None
    notation: str | None

def load_schema(path: Path | None = None,
                vocabularies: Vocabularies | None = None) -> Schema: ...
    # default: the packaged file; gives each field that has allowed values an enum

def allowed_values(field: Field, vocabularies: Vocabularies) -> tuple[AllowedValue, ...]: ...
    # the values of the field's vocabulary, else the hand-written ones, else ()

def field_for_column(schema: Schema, column_name: str) -> Field: ...   # KeyError naming the name
```

- `load_schema()` reads the packaged file with `importlib.resources`, so it works from a wheel,
  passes it to `Schema.from_descriptor`, and takes the vocabulary files from the cache,
  downloading them on first use, or from the `Vocabularies` it is given (FR-010).
- The complete Table Schema (FR-019) is the loaded schema: `schema.to_descriptor()` and
  `schema.to_json(path)` write it with the `enum` on every field that has allowed values.
- A field is looked up by its code with `Schema.get_field`, and by its published column name with
  `field_for_column`.
- `ghfdb.fields` re-exports `load_schema`, `allowed_values`, `field_for_column`, `AllowedValue`,
  `Vocabularies`, `caching_session` and `MissingSchemeError`.

### `ghfdb.fields.vocabularies`

```python
class Vocabularies:
    """The vocabulary files a field schema points at, cached on disk."""
    def __init__(self, session: Session | None = None) -> None: ...
    def allowed_values(self, vocabulary: Mapping[str, str | None]) -> tuple[AllowedValue, ...]: ...
        # raises MissingSchemeError(scheme or collection identifier) when the file lacks it
    def graph(self, scheme: str) -> Graph: ...     # downloads <scheme>.ttl when absent or old

def caching_session(directory: Path | None = None) -> Session: ...

class MissingSchemeError(LookupError):
    """Names the field code and the scheme or collection that is not defined."""
```

- Only the scheme files a field needs are read. A collection is found by its identifier in the scheme's file. The members
  of a `skos:OrderedCollection` keep the collection's order; every other list is sorted by term.
- The download is the scheme's identifier with `.ttl` added, through a `requests-cache`
  `CachedSession` (filesystem backend, `cache_control=True`, `expire_after=0`,
  `stale_if_error=True`, two retries on 502, 503 and 504). The server's `ETag`, `Last-Modified`
  and `Cache-Control` decide freshness, so an unchanged file costs a `304` and no fixed expiry
  hides a change. The cache is `vocabularies` in `platformdirs.user_cache_dir("ghfdb")`, or the
  directory passed to `caching_session`. `Vocabularies` takes a session.
- `rdflib` is imported by this module, which `ghfdb.fields` imports.

### The vocabulary checks (FR-017)

The cache of the test session starts empty, in a temporary directory (`tests/conftest.py`), so the
tests load the shipped schema against the files as currently published. One test checks that every scheme and collection the
schema links to is defined in its file. Small synthetic vocabularies under
`tests/test_fields/vocabularies/` cover the reading itself, including ordered collections, and `responses`
stands in for the web to cover the download, revalidation with the `ETag`, a changed file, an
unreachable server and a failed or non-Turtle download.

### The documentation

- `docs/conf.py` puts `docs` on `sys.path` and lists `extensions.field_reference`,
  `sphinx.ext.autodoc` and `sphinxcontrib.mermaid`.
- `docs/extensions/field_reference.py` connects to `source-read` and renders the pages under
  `reference/fields/` as Jinja2 templates. A page calls `index()` or `entries("parent")`, which
  are macros in `docs/extensions/templates/field_reference.md.jinja`, and the Markdown comes from
  the schema `load_schema()` returns. On `builder-inited` it writes the complete Table Schema,
  `schema.to_json()`, into the
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
- `pyproject.toml`: the `frictionless`, `platformdirs`, `rdflib`, `requests` and `requests-cache`
  dependencies, the development and documentation dependencies, `docs` in mypy's files and
  pytest's `pythonpath`, `types-openpyxl`.

## Complexity Tracking

| Choice | Why it is needed | Simpler alternative rejected because |
|---|---|---|
| Dependency `frictionless` | It reads the schema into types that already exist, validates it, and writes it back out | Dataclasses restating its fields, and a loader, would be code to keep in step with the file |
| Dependency `rdflib` | Parsing Turtle and SKOS by hand is a parser this repository would own | Parsing N-Triples with a regular expression handles one format, and every SKOS query would be hand-written |
| A Sphinx extension | The reference must never disagree with the schema (FR-013) | Committed generated pages need a second check that they are current, and can drift between runs |
