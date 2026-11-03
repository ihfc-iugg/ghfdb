# ADR 0003 — Vocabulary terms are read from the published release, never copied

**Status:** accepted

## Decision

The field schema, `ghfdb/fields/schema.json`, is written by hand and holds no vocabulary term.

- The schema states the IHFC Controlled Vocabularies release it uses once, at the top: its
  version, its DOI and the address of the repository that publishes it.
- A vocabulary field states where its terms come from: the concept scheme by name, the
  collection that narrows the choice where there is one, and whether a term is written as the
  concept's label or its notation. It holds no concept address, no list of values and no `enum`.
- The vocabulary files are not stored in this repository. The first time the package needs a
  release it downloads `vocabularies-full.zip` from that release on GitHub, unpacks the Turtle
  files into a cache directory outside the repository, keyed by version, and reads them from
  there afterwards. The cache is in the user's cache directory, or where `GHFDB_VOCABULARY_CACHE`
  points.
- `FieldSchema.load()` reads the allowed values from the cached release. The members of a
  `skos:OrderedCollection` keep the collection's order. Every other list is sorted by term.
- A Frictionless Table Schema with an `enum` on each field is built in memory by
  `FieldSchema.descriptor()`. It is never written back to `schema.json`. The documentation's
  downloadable schema and the validation of the schema file both use it.
- The tests use the real published release. One test fails when the vocabularies publish a
  release newer than the one the schema states. Only published releases count, never the
  vocabularies' main branch.

## Why

`CONSTITUTION.md` Article XI rules out typing a vocabulary term by hand. The earlier approach
kept a copy of the release in this repository and copied its terms into the schema with a
command, then tested that the copy still matched. That left three copies of the same terms, and
a step a maintainer had to remember. Reading the terms from the release itself leaves one
source, and makes a change in the vocabularies show up as a failing test, which is wanted: the
people who maintain the schema should hear about it the day a release is published.

The schema names a scheme by the name of its file in the release, so the package opens only the
files a field needs. A concept scheme moving to a new address between releases changes nothing
in the schema, because no address is written there.

Downloading costs a first load that needs the network, and it means a release that disappears
from GitHub breaks the first load on a new machine. Releases are archived with a DOI, and a
cached release keeps working offline.

## Revisit if

The vocabularies stop publishing `vocabularies-full.zip` with their releases, or a field's
allowed values stop being one scheme or one collection of a scheme.
