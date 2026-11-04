# ADR 0004 — The field schema is read with Frictionless

**Status:** accepted. It supersedes the way [ADR 0003](0003-vocabularies-are-read-from-their-permanent-identifiers.md)
reads the schema file and holds its fields, and where that decision puts the download cache. The
rest of ADR 0003 stands.

## Decision

`ghfdb/fields/schema.json` is read by Frictionless, and the package uses Frictionless's own types.

- `load_schema()` passes the file to `frictionless.Schema.from_descriptor` and returns the
  `frictionless.Schema`. ghfdb defines no field class and no schema class. The facts Table Schema
  has no property for (published column name, obligation, domain, quality relevance, unit and the
  rest) stay in each field's `custom` dictionary, where Frictionless keeps them and writes them
  back.
- A vocabulary field's `vocabulary` object is read as written in the file. There is no class for
  it.
- What Frictionless cannot do stays in this repository: resolving each vocabulary field's allowed
  values from the vocabularies into the field's `enum` constraint, in memory only, and finding a
  field by its published column name (`field_for_column`). A field is found by its code with
  Frictionless's `get_field`, and the complete schema is the loaded schema, written with
  `to_descriptor()` or `to_json()`.
- `AllowedValue` stays, as a small frozen type, because Table Schema has no place for the label,
  URI and notation of an allowed value and the field reference links every term to its concept.
- The download cache is the `vocabularies` directory in `platformdirs.user_cache_dir("ghfdb")`, or
  the directory passed to `caching_session`. The `GHFDB_VOCABULARY_CACHE` environment variable is
  gone: nothing but the tests used it, and they pass a directory.
- The field reference is rendered from Jinja2 templates, and the tests stand in for the web with
  `responses`.
- `frictionless`, `platformdirs` and (for the documentation) `jinja2` are declared dependencies.

## Why

`CONSTITUTION.md` Articles II and VII prefer an established, maintained package to custom code and
rule a package's size out as a reason against it. The first version of the field schema read the
file with `json` into frozen dataclasses that restated the Frictionless types, on the ground that
Frictionless was a large dependency. That put a loader, three classes and a lookup table in this
repository to keep in step with a file that Frictionless already reads, validates and writes
back. A field added to the schema meant a change to the file and a change to the classes. With
Frictionless's types there is one place to change.

The functions that work on a `frictionless.Schema` are module-level because the type is not ours to
extend. A class wrapping it would be the restatement this decision removes.

## Revisit if

Frictionless stops keeping unknown field properties in `custom`, or Table Schema gains a place for
the label and URI of each allowed value, which would remove `AllowedValue`.
