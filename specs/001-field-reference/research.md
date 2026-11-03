# Research: A field reference for the upload template

The investigation behind `plan.md`. Every answer below was read from the source it names.

## Sources read

| Source | What was taken from it |
|---|---|
| The current upload template, `template.xlsx` as distributed with the GHFDB portal, sheet `data list` | Rows 1–8 of the 70 field columns: field code, obligation, domain, quality relevance, name, published column name, unit, allowed range. The sheet `controlled vocabulary` shows how terms are written in a cell. |
| Fuchs et al. (2023), Appendix A, as the spreadsheet `Appendix_A.XLSX` | Every field's type, meaning (`Field Description`), and the paper's own name, unit, obligation, domain, quality relevance and range, for comparison with the template. It covers all 70 fields, `A1`–`A8` included, with codes written `P01`, `C01`. |
| IHFC Controlled Vocabularies v2026.1, the GitHub release `v2026.1` of `ihfc-iugg/controlled-vocabularies` (DOI 10.5880/fidgeo.2026.065) | 15 concept schemes, one Turtle file each, with labels, notations, collections and a scope note naming the fields each scheme serves. |
| FS-002, `specs/002-upload-template/spec.md` | What the generated template reads from the field definitions. |

## The vocabulary release

- **Which schemes serve which fields is stated in the release.** Every scheme's `skos:scopeNote`
  reads "Lists the values allowed in the field(s) … of the Global Heat Flow Database", naming the
  published column names. All 25 vocabulary fields are named, and every scheme serves at least one:

  | Scheme | Fields |
  |---|---|
  | `geographic-environments` | P7 |
  | `exploration-methods` | P12 |
  | `exploration-purpose` | P13 |
  | `heat-flow-method` | C3 |
  | `heat-flow-corrections` | C11–C19 |
  | `heat-flow-probes` | C21 |
  | `temperature-method` | C31, C32 |
  | `temperature-corrections` | C35, C36 |
  | `conductivity-sources` | C41 |
  | `conductivity-location` | C42 |
  | `conductivity-methods` | C43 |
  | `conductivity-saturation` | C44 |
  | `conductivity-conditions` | C45 |
  | `conductivity-pt-function` | C46 |
  | `conductivity-strategy` | C48 |

- **Collections.** Only `heat-flow-corrections` groups concepts into collections that name fields
  (`skos:definition`): `insitu` serves `corr_IS_flag` (C11), `temperature` serves `corr_T_flag`
  (C12), `generic` serves C13–C19. The other schemes' collections (laboratory methods, pressure or
  temperature functions) group concepts by kind and name no field, so those fields take the whole
  scheme.
- **Concept URIs** in v2026.1 are under `https://portal.heatflow.world/vocabularies/`. The
  vocabularies' main branch has since moved to `w3id.org` addresses, unreleased. The field schema
  records the URIs of the stated release, never of the main branch.
- **No version inside the files.** The release's Turtle files carry the DOI (`dcterms:isPartOf` on
  every scheme) but no version string. The version is named by whoever adopts the release, and the
  DOI is read from the files.
- **How a term is written in a cell.** The template writes most terms as the concept's label in
  square brackets (`[Bullard method]`), and the temperature methods by their notation (`[LOGeq]`).
  `conductivity-saturation` also publishes notations (`drymeas`), but the template writes its
  labels (`[Recovered]`). Two concepts of `temperature-method`, `Other` and `Unspecified`, have no
  notation. So the form is a property of the field, read from the template, and a concept with no
  notation is written by its label.
- **Labels changed between the template and v2026.1.** The template's own choice lists hold older
  labels (`[Considered – p]`, `[Bullard plot]`, `[Lab - line source / full space]`). v2026.1 keeps
  them as `skos:altLabel` or `skos:hiddenLabel` and publishes new preferred labels
  (`Pressure considered`, `Bullard method`, `Lab - line source - full space`). The allowed term is
  the preferred label of the stated release. The older forms are the release's business, read by
  the later checks (R3) when they suggest a term.

## Where the template and Appendix A disagree

Read field by field. Under D-3 the template is followed, and each disagreement is recorded as a
decision of its own (D-12 to D-22 in `decisions.md`).

| Fields | Template | Appendix A |
|---|---|---|
| P4, P5, P10, P11, C8, C20, C35, C36, C47 | names such as "Geographical latitude", "Primary reference", "TC number" | "Latitude (Geographical)", "Primary data reference", "Thermal conductivity number" |
| C37 | "Number of temeprature recordings" | "Number of temperature recordings" |
| C46, C49 | `tc_pT_fuction`, `Ref_ISGN` | `tc_pT_function`, `Ref_IGSN` (already D-2) |
| A8 | published column name `ID` | none |
| P11, C23, C33, C34, C38 | units `m`, `degree`, `hr`, `hr`, `YYYY-MM` | `-`, `deg`, `hours`, `hours`, `-` |
| C2, C37 | obligation `R` | `M` |
| A1–A8 | obligation `-` | `A` |
| P12, C20 | domain `B,S` | `B`, `S` |
| P6 | quality relevance `M score` | `M score (probe sensing)` |
| C46 | quality relevance `M score` | `-` |
| C4, C5, C6 | range to one decimal place (`0 - 19,999.9`) | two decimal places |
| C23 | range `0 – 99.9` | `0 – 90` |
| C27–C30 | range written `– 99,999.99 – 99,999.99` | `-99,999.99 – 99,999.99` |
| A1, A3–A7 | range `-` | a choice box, or a date |

Everything else agrees, once spacing and the separator in `12000`/`12,000` are set aside.

Appendix A is the only source of each field's **type** and **meaning**. Its types are `Float (n
decimal places)`, `Integer (n)`, `Char (255)`, `POSIX date (YYYY-MM)`, `BIT field` and `Boolean
field`. Appendix A gives no meaning for `A1`–`A8`.

## Answers the plan needs

### How the field schema is held and who writes which part

The field schema is one JSON file, `ghfdb/fields/schema.json`, a Frictionless Table Schema,
shipped inside the package and written entirely by hand, each fact with its source. It names the
vocabulary release once and, for each vocabulary field, the concept scheme and collection, and
holds no term, no concept address and no `enum`. The allowed values are read from the release when
the schema is loaded. That is what makes FR-005, FR-015 and FR-017 checkable: there is no copy of
the terms to fall out of step, and a check against the real release can only fail because the
vocabularies changed.

A separate hand-written source file (YAML or TOML) generating the JSON was weighed. It would hold
the same facts in a second format and add a build step between the source and what ships, for no
reader who needs it.

### Frictionless Table Schema shape

- `name` is the field code, because the template's header row holds field codes and a Frictionless
  validator matches `name` against the header.
- `title` is the name, `description` the meaning, `type` the Frictionless type (`number`,
  `integer`, `string`), `constraints` the range (`minimum`, `maximum`), the format (`pattern`) and,
  for a single-valued field with a fixed list, `enum`.
- The schema's `missingValues` is `[""]`: an empty cell and nothing else (FR-008, D-4).
- Facts with no Frictionless property are recorded as additional properties, which the Table Schema
  specification permits on a field descriptor: the published column name and its earlier spelling,
  group, unit, obligation, domain, quality relevance, decimal places, vocabulary binding, allowed
  values, separator for several values, guidance, and the source of each fact. The stated release
  is an additional property of the schema.
- `required` is not set on any field: obligation depends on the domain, and which domain a child is
  in is a cross-field rule (R4).

### Loading the schema needs no dependency

The standard library reads JSON, and frozen dataclasses hold the result. `frictionless` would
read it too, but it is a large runtime dependency with its own field classes, and the package
needs none of its behaviour to look a field up. It is a development dependency, used to validate
the shipped schema independently (SC-006).

### Reading a vocabulary release

`rdflib` parses the Turtle files and answers the SKOS questions (scheme, collection members,
ordered collection lists, labels, notations, `isPartOf`). Loading the field schema needs it, so it
is a runtime dependency.

### The stored release

The Turtle files of the stated release are not kept in the repository or in the package. The
GitHub release publishes each vocabulary as `.ttl`, `.rdf`, `.nt` and `.jsonld`, plus
`vocabularies-full.zip` holding all of them, and the `.ttl` files in the zip are byte for byte the
files of the release's assets. The package downloads the zip once, from the repository and version
the schema names, keeps the `.ttl` files in a cache directory keyed by version, and reads them
from there. A reader who wants the releases' terms of use finds them with the release.

### The template as a test source

A copy of the current template is kept under `tests/sources/` and read with `openpyxl` (a
development dependency), so a test confirms that every fact the field schema attributes to the
template is what the template says. Appendix A is not copied into the repository: it is the
publisher's supplementary material. Facts sourced to it are checked in review.

### The field reference in the documentation

A Sphinx extension in `docs/extensions/` renders the field entries from the loaded field schema while the
documentation builds, so the reference cannot disagree with the schema (FR-013). It also copies
the schema file into the built site, so the page links to the exact file it documents. Diagrams
use `sphinxcontrib-mermaid`. The Python API page is generated from docstrings with
`sphinx.ext.autodoc`, as the documentation standard requires.

## Planning notes

The specification directory has no `planning-notes.md`.

## What already exists

```
field definitions loader          · 4, standard library · json, dataclasses, importlib.resources
schema validity check             · 6, maintained package · frictionless (development only)
reading a vocabulary release      · 6, maintained package · rdflib
reading the template in tests     · 6, maintained package · openpyxl (development only)
markdown entries for the docs     · 7, new · searched myst-parser and sphinx for a table-schema renderer; none
diagrams in the docs              · 6, maintained package · sphinxcontrib-mermaid
python API page                   · 3, package · sphinx.ext.autodoc
adopting a release and its report · 7, new · searched the vocabularies repository; it publishes files, no client
```

This repository holds no code yet beyond two empty packages, so nothing under 2 applies.
