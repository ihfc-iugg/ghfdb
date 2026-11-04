# How the vocabularies are fetched

The field schema links each vocabulary field to the permanent identifier of its concept scheme
and, where it narrows the choice, of a collection. It holds no term. The terms are read from the
IHFC Controlled Vocabularies as currently published, so there is nothing to adopt or move when
the vocabularies change. This page explains where the files come from and what to do when a test
reports a change.

## Where the files come from

A concept scheme is published at its identifier with `.ttl` added. For
`https://w3id.org/ihfc-iugg/vocabularies/exploration-methods` the file is
`https://w3id.org/ihfc-iugg/vocabularies/exploration-methods.ttl`. The package downloads the file
the first time a field needs it and keeps it in a cache directory outside the repository:

- `$GHFDB_VOCABULARY_CACHE` when that variable is set
- otherwise `$XDG_CACHE_HOME/ghfdb/vocabularies`, or `~/.cache/ghfdb/vocabularies`

The file is cached under the last segment of the identifier, such as `exploration-methods.ttl`.
A cached file older than a week is downloaded again, and the old copy stays in use when the
download fails. To refresh everything now, delete the cache directory.

## What the tests do

The cache of a test session starts empty, in a temporary directory, so every test run and every
CI run reads the files as currently published. The tests fail on their own when the vocabularies
change in a way that matters here:

- A scheme or collection the schema links to is no longer defined in the file at its identifier.
  The failure names the field.
- A concept has no English preferred label.
- A template, a field reference page or another test depended on a term that moved or was removed.

## Respond to a change in the vocabularies

1. Run `uv run pytest` and read which fields the failures name.
2. If a scheme or collection was renamed, change the identifier in `ghfdb/fields/schema.json` by
   hand to the new one.
3. If a term moved or was removed, fix what depended on it, and say so in the pull request:
   existing workbooks may no longer pass the check.
4. Add a line under `## [Unreleased]` in `CHANGELOG.md` when users of the package can see the
   difference.

See [ADR 0003](../adr/0003-vocabularies-are-read-from-their-permanent-identifiers.md) for why
the schema works this way and [the Python API](../reference/python-api.md) for the classes
involved.
