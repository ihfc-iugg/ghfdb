# ADR 0001 — The field schema keeps hand-written and generated facts apart

**Status:** superseded by [ADR 0003](0003-vocabularies-are-read-from-the-published-release.md)

## Decision

The field schema is one Frictionless Table Schema file, `src/ghfdb/fields/schema.json`, shipped
inside the package and read with the standard library.

- Every fact about a field is written by hand, with its source, **except** the facts that come
  from the IHFC Controlled Vocabularies: the concept scheme and collection URIs, the allowed
  values and their `enum`, and the stated vocabulary release.
- A vocabulary field names its scheme and collection by the last segment of their URI
  (`conductivity-methods`, `insitu`). The full URIs are generated.
- Only `ReleaseMove` (`python -m ghfdb.fields.release`) writes the generated facts, from the
  release's Turtle files kept under `vocabularies/<version>/`.
- A test regenerates the generated facts from the stored release and fails on any difference.
- The file has one serializer, `json.dumps(..., indent=2, ensure_ascii=False)` and a trailing
  newline.

## Why

`CONSTITUTION.md` Article XI rules out typing a vocabulary term by hand, and the old checking tool
drifted from the published vocabularies because its copies were edited by hand. Keeping the two
kinds of fact apart, with one writer for the generated kind, makes that rule checkable: the test
can rebuild exactly what the release says and compare.

The binding is written by name because scheme URIs move between releases (the vocabularies' main
branch has moved them to `w3id.org`). A hand-written URI would need a hand edit at the first
move. A second hand-written source format generating the JSON was weighed and rejected: it would
hold the same facts twice and add a build step between the source and what ships.

## Revisit if

The vocabularies publish a release in which a scheme's last URI segment changes, or a field's
allowed values stop being exactly one scheme or one collection.
