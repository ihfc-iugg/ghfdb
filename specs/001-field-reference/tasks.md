# Tasks: A field reference for the upload template

**Input**: `plan.md`, `research.md`, `decisions.md` and `spec.md` in this directory.

**Tests**: every behaviour below is written test-first, per
`docs/contributing/standards/testing.md`. No test asserts wording or layout.

**Order**: US2 is built first, because the documentation (US1) is rendered from the field
definitions and the release step (US3) rewrites them. Within a story, groups run in order, and each
leaves the tree green.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: User Story 2 - A developer loads the field definitions (Priority: P1)

**Goal**: `FieldSchema.load()` returns all 70 fields, looked up by field code or published column
name, with every fact and its source, from a valid Frictionless Table Schema shipped in the package.

**Independent Test**: load the field definitions with no network, look fields up by code and by
column name, and validate `schema.json` with `frictionless`.

### Group 1 — dependencies, the stored release, and reading it

- [ ] T001 [US2] `pyproject.toml`: optional extra `vocabularies = ["rdflib>=7"]`; development
  dependencies `frictionless>=5`, `openpyxl>=3.1`, `rdflib>=7`; documentation dependency
  `types-openpyxl`; documentation dependency `sphinxcontrib-mermaid>=1`; `/vocabularies` added to the
  sdist include list; `docs` added to mypy's `files` and to pytest's `pythonpath`; `uv lock`.
  deptry stays clean.
- [ ] T002 [US2] Copy the 15 Turtle files (`.ttl` only) and the release-root `LICENSE` of the v2026.1 release into
  `vocabularies/2026.1/`, and the current upload template into `tests/sources/upload-template.xlsx`.
- [ ] T003 [US2] `src/ghfdb/fields/schema.py`: the frozen dataclasses `VocabularyRelease`,
  `VocabularyBinding` and `AllowedValue` (plan.md, "`ghfdb.fields.schema`").
- [ ] T004 [US2] `src/ghfdb/fields/release.py`: `ReleaseFiles` and `MissingSchemeError`. The DOI is
  read from `dcterms:isPartOf`, the same on every scheme. `allowed_values(binding)` finds the scheme and collection by name (the last segment of
  their URI, plan.md "The field schema file"), returns their URIs, and the
  scheme's concepts, or the collection's members where the binding names a collection, each as an
  `AllowedValue` with its term written per D-20 and sorted per D-21, and raises
  `MissingSchemeError` naming the scheme or collection the release lacks. Tested on small test
  releases under `tests/test_fields/releases/`.
- [ ] T005 [US2] `ReleaseMove(schema_path, release).apply()`: rewrites `vocabulary.scheme`,
  `vocabulary.collection`, `allowedValues` and `constraints.enum` of every field with a
  `vocabulary`, and `vocabularyRelease`, leaving every other property as it was, and writes the
  file with the one serializer plan.md names.

### Group 2 — loading and looking up

- [ ] T006 [US2] `FieldSchema.load(path=None)` reading the packaged `schema.json` through
  `importlib.resources`, `fields` in file order, iteration, `len`, and `__getitem__` by field code
  or published column name. `UnknownFieldError(KeyError)` names the key. Tested on a small test
  schema file.
- [ ] T007 [US2] `src/ghfdb/fields/__init__.py` re-exports the public names, and importing
  `ghfdb.fields` does not import `rdflib`.

### Group 3 — the 70 fields

- [ ] T008 [US2] Author `src/ghfdb/fields/schema.json`: all 70 fields in field-code order, every
  property of plan.md "The field schema file", every fact with its source, per `research.md` and
  decisions D-1 to D-23. Vocabulary bindings per research.md "The vocabulary release". C38 and A3 use `valueFormat`,
  never `format`. Then produce the file's final form by running `ReleaseMove` against
  `vocabularies/2026.1/`: allowed values and URIs are never written by hand.
- [ ] T009 [US2] Tests on the shipped schema: 70 fields, field-code order, unique codes and
  column names; every fact sourced to the template equals `tests/sources/upload-template.xlsx`
  (with D-2, D-12, D-13, D-16 and D-17 applied); the `sources` keys of every field are exactly the keys of plan.md's
  source table, iterated from that table and not from the file, every source is a known code, and every `decision:D-<n>` exists in `decisions.md`; `missingValues` is `[""]`; `constraints.enum` equals
  the allowed terms wherever a field has allowed values; the file equals its own serialization;
  the file is a valid Table Schema to `frictionless`.
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
  release; C25, C26 and C49 give their separator; C46 and C49 give their earlier spelling; the
  index links every field.
- [ ] T013 [US1] Pages `docs/reference/fields/index.md` (what the reference is, the index, where
  the facts and allowed values come from and how a newer release is adopted, each with a
  simplified Mermaid diagram, and the schema download), `parent.md`, `child.md`,
  `assessment.md`; `fields/index` added to the Reference contents. The documentation builds with `-W`.

**Checkpoint**: an assessor can look up any field.

---

## Phase 3: User Story 3 - A developer moves the field reference to a newer vocabulary release (Priority: P2)

**Goal**: a maintainer adopts a newer release in one step that changes only allowed values, the
stated release and the changelog, and reports per field what changed.

**Independent Test**: move a copy of the schema from a test release to a second test release that
adds, removes and relabels concepts, and compare.

### Group 1 — the release step

- [ ] T014 [US3] `ReleaseMove.changes()`: one `FieldChange` per vocabulary field, in field-code
  order, with the concepts added, removed and relabelled (same URI, new term), empty for an
  unchanged field.
- [ ] T015 [US3] `ReleaseMove.apply()` resolves every field before writing: a release lacking a
  scheme or collection a field names raises `MissingSchemeError` naming the field and the scheme,
  and the file is unchanged; on success nothing but `allowedValues`, `constraints.enum` and
  `vocabularyRelease` differs.
- [ ] T016 [US3] `main()`, run as `python -m ghfdb.fields.release <version> <directory>`: prints
  the per-field report, adds the changelog line naming the old and new release under
  `## [Unreleased]` → `### Changed`, creating that heading when it is absent, exits 1 with the field and scheme on a missing scheme.
- [ ] T017 [US3] The drift check: a test regenerates every vocabulary field's scheme and collection
  URIs and allowed values from `vocabularies/<stated version>/`, checks `constraints.enum` equals
  the allowed terms and the release's DOI equals the stated one, and fails naming every field that
  differs.
- [ ] T018 [US3] `docs/contributing/vocabulary-release.md`, the maintainer's how-to for adopting a
  release, linked from the field reference's opening page; `docs/reference/python-api.md` gains
  `ghfdb.fields.release`.

**Checkpoint**: a newer release can be adopted.
