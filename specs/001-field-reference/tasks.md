# Tasks: A field reference for the upload template

**Input**: `plan.md`, `research.md`, `decisions.md` and `spec.md` in this directory.

**Tests**: every behaviour below is written test-first, per
`docs/contributing/standards/testing.md`. No test asserts wording or layout.

**Order**: US2 is built first, because the documentation (US1) is rendered from the field
definitions and the vocabulary checks (US3) read them. Within a story, groups run in order, and each
leaves the tree green.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: User Story 2 - A developer loads the field definitions (Priority: P1)

**Goal**: `FieldSchema.load()` returns all 70 fields, looked up by field code or published column
name, with every fact and its source, from a valid Frictionless Table Schema shipped in the package.

**Independent Test**: load the field definitions, look fields up by code and by
column name, and validate the complete Table Schema built from `schema.json` with `frictionless`.

### Group 1 — dependencies, the test sources, and reading the vocabularies

- [ ] T001 [US2] `pyproject.toml`: runtime dependency `rdflib>=7`; development
  dependencies `frictionless>=5`, `openpyxl>=3.1`; documentation dependency
  `types-openpyxl`; documentation dependency `sphinxcontrib-mermaid>=1`; `docs` added to mypy's `files` and to pytest's `pythonpath`; `uv lock`.
  deptry stays clean.
- [ ] T002 [US2] Copy the current upload template into `tests/sources/upload-template.xlsx`. The
  vocabulary files are never copied into the repository.
- [ ] T003 [US2] `ghfdb/fields/vocabularies.py`: the frozen dataclasses `VocabularyBinding` and
  `AllowedValue` (plan.md, "`ghfdb.fields.vocabularies`").
- [ ] T004 [US2] `ghfdb/fields/vocabularies.py`: `Vocabularies`, `MissingSchemeError`, the cache
  directory and the download of `<scheme>.ttl` through a `requests-cache` session that
  revalidates with the server's `ETag` and `Cache-Control`. `allowed_values(binding)` reads the file named for the scheme,
  checks the scheme and collection identifiers are defined in it, and returns the scheme's
  concepts, or the collection's members, each as an `AllowedValue` with its term written per D-20
  and sorted per D-21 (an ordered collection keeps its order). It raises `MissingSchemeError`
  naming the scheme or collection that is not defined. Tested on small test vocabularies under
  `tests/test_fields/vocabularies/` and on files published in a local directory.

### Group 2 — loading and looking up

- [ ] T006 [US2] `FieldSchema.load(path=None, vocabularies=None)` reading the packaged `schema.json` through
  `importlib.resources` and resolving each vocabulary field against the vocabularies, `fields` in file order, iteration, `len`, and `__getitem__` by field code
  or published column name. `UnknownFieldError(KeyError)` names the key. `descriptor()` builds the complete Table Schema in
  memory. Tested on a small test schema file and small test vocabularies.
- [ ] T007 [US2] `ghfdb/fields/__init__.py` re-exports the public names.

### Group 3 — the 70 fields

- [ ] T008 [US2] Author `ghfdb/fields/schema.json`: all 70 fields in field-code order, every
  property of plan.md "The field schema file", every fact with its source, per `research.md` and
  decisions D-1 to D-23. Vocabulary bindings per research.md "The vocabularies". C38 and A3 use `valueFormat`,
  never `format`. The file holds no allowed value of a vocabulary field and no concept address: they are read
  from the published vocabularies.
- [ ] T009 [US2] Tests on the shipped schema: 70 fields, field-code order, unique codes and
  column names; every fact sourced to the template equals `tests/sources/upload-template.xlsx`
  (with D-2, D-12, D-13, D-16 and D-17 applied); the `sources` keys of every field are exactly the keys of plan.md's
  source table, iterated from that table and not from the file, every source is a known code, and every `decision:D-<n>` exists in `decisions.md`; `missingValues` is `[""]`; the file holds no `enum` and the complete descriptor's `enum` equals
  the allowed terms wherever a field has allowed values; the file equals its own serialization;
  the file and the complete descriptor are valid Table Schemas to `frictionless`.
- [ ] T010 [US2] Documentation: `sphinx.ext.autodoc` and `sphinxcontrib.mermaid` registered in
  `docs/conf.py`; `docs/reference/index.md` listing `python-api` only;
  `docs/reference/python-api.md` (autodoc of `ghfdb.fields`); the developer guide
  `docs/developer/field-definitions.md` (loading the field definitions and looking a field up); the
  Reference and Developer guide sections in `docs/index.md`, a README paragraph with
  a short example, `CHANGELOG.md` under Unreleased → Added, and the `CONTEXT.md` entries of FR-018.

**Checkpoint**: the field definitions load and are complete.

---

## Phase 2: User Story 1 - A data assessor looks up a field in the documentation (Priority: P1)

**Goal**: the built documentation has a field reference with one entry per field, reachable by
field code and column name, every fact with its source, rendered from the field schema.

**Independent Test**: build the documentation, open the field reference, and reach `C43` and
`tc_method` from the opening page.

### Group 1 — the field reference

- [ ] T011 [US1] `docs/extensions/field_reference.py`: on `source-read`, replace `{field-index}` with the
  index table and `{field-entries} <group>` with that group's entries (plan.md, "The
  documentation"); on `builder-inited`, copy `schema.json` to
  `docs/reference/fields/ghfdb-field-schema.json`, listed in `.gitignore`. Registered in
  `docs/conf.py` as `extensions.field_reference`, with `docs` on `sys.path`.
- [ ] T012 [US1] Tests in `tests/test_docs/test_extensions/test_field_reference.py`, on the generated Markdown:
  each field has exactly one entry, on its group's page, in field-code order; each entry carries a
  target for its code and for its column name; every fact of the field appears with its source;
  a vocabulary field lists every allowed term linked to its concept URI, with its scheme and the
  vocabulary; C25, C26 and C49 give their separator; C46 and C49 give their earlier spelling; the
  index links every field.
- [ ] T013 [US1] Pages `docs/reference/fields/index.md` (what the reference is, the index, where
  the facts and allowed values come from and how the allowed values stay current, each with a
  simplified Mermaid diagram, and the schema download), `parent.md`, `child.md`,
  `assessment.md`; `fields/index` added to the Reference contents. The documentation builds with `-W`.

**Checkpoint**: an assessor can look up any field.

---

## Phase 3: User Story 3 - A developer finds out when the vocabularies change (Priority: P2)

**Goal**: the allowed values follow the published vocabularies with no edit to the field schema,
and the checks fail when the vocabularies change beneath it.

**Independent Test**: point a vocabulary field at a collection its file does not define and
confirm loading fails and names the field.

### Group 1 — the vocabulary checks

- [ ] T014 [US3] A scheme or collection its published file does not define raises
  `MissingSchemeError` naming the field and the identifier when the schema is loaded.
- [ ] T015 [US3] The test session's cache starts empty (`tests/conftest.py`), so the tests read
  the vocabularies as currently published.
- [ ] T016 [US3] A test checks that every scheme and collection the shipped schema links to is
  defined in the file downloaded from its identifier.
- [ ] T017 [US3] `docs/contributing/vocabularies.md`, where the files come from, how the cache is
  refreshed and what to do when a test reports a change, linked from the field reference's
  opening page.

**Checkpoint**: a change in the vocabularies reaches the allowed values and the checks report it.

---

## Fixes made while accepting the stories

- [x] T019 [US2] Keep each test beside the module it tests, and name the public classes on the
  API page.
- [x] T020 [US1] Drop a test that asserted the documentation extension's call sequence; the
  documentation build proves the registration.

## Fixes from the code review

- [x] T024 [US2] C38 accepts a range of months, as Appendix A describes (D-28).
- [x] T025 [US1] A pipe in a fact is escaped once in the entry's table, and a test holds the first
  facts of every entry in their order.
