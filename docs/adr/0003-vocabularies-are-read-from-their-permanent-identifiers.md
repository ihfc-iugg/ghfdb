# ADR 0003 — Vocabulary terms are read from the vocabularies' permanent identifiers

**Status:** accepted

## Decision

The field schema, `ghfdb/fields/schema.json`, is written by hand and holds no vocabulary term.

- A vocabulary field links to the permanent identifier of its concept scheme, such as
  `https://w3id.org/ihfc-iugg/vocabularies/exploration-methods`. Where the field takes only some
  of the scheme's concepts, it also links to the identifier of the `skos:Collection` or
  `skos:OrderedCollection` that narrows the choice, such as
  `https://w3id.org/ihfc-iugg/vocabularies/heat-flow-corrections/insitu`. It also says whether a
  term is written as the concept's label or its notation. It holds no list of values and no `enum`.
- The schema declares no release, version or DOI. Data assessors do not choose which version of
  the vocabularies they use: the terms are those currently published at the identifiers.
- The vocabulary files are not stored in this repository or in the package. A scheme is published
  at its identifier with `.ttl` added, so the package downloads that file the first time it needs
  the scheme and keeps it in a cache directory outside the repository, named for the scheme. A
  cached file older than a week is downloaded again, and the old copy is kept when the download
  fails. The cache is in the user's cache directory, or where `GHFDB_VOCABULARY_CACHE` points.
  Deleting the directory forces a fresh download.
- `FieldSchema.load()` reads the allowed values from the cached files. The members of a
  `skos:OrderedCollection` keep the collection's order. Every other list is sorted by term.
- A Frictionless Table Schema with an `enum` on each field is built in memory by
  `FieldSchema.descriptor()`. It is never written back to `schema.json`. The documentation's
  downloadable schema and the validation of the schema file both use it.
- The cache of a test session starts empty, so the tests always read the files as currently
  published, and CI does the same. A test checks that every scheme and collection the schema links
  to is defined in the file downloaded from its identifier.

## Why

`CONSTITUTION.md` Article XI rules out typing a vocabulary term by hand. An earlier approach kept
a copy of a stated release in this repository and copied its terms into the schema with a command.
That left three copies of the same terms and a step a maintainer had to remember. It also made a
version the schema's business, when nobody who fills in a workbook picks one.

Pointing at the permanent identifiers leaves one source. A change in the vocabularies shows up as
a failing test, which is wanted: the people who maintain the schema should hear about it the day
the vocabularies change. An identifier that moves is the vocabularies' responsibility, because it
is permanent by promise, and the schema holds nothing else that could go stale.

The costs are a first load that needs the network, and terms that can change between two uses of
the same package version. The week-long cache bounds the second, and a cached copy keeps working
offline.

## Revisit if

The vocabularies stop publishing a Turtle file at each scheme's identifier, or a field's allowed
values stop being one scheme or one collection of a scheme.
