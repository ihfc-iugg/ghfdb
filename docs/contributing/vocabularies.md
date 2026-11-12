# How the vocabularies are fetched

The field schema links each vocabulary field to the permanent identifier of its concept scheme
and, where it narrows the choice, of a collection. It holds no term. The terms are read from the
IHFC Controlled Vocabularies as currently published, and for lithology and stratigraphic age from
the two external vocabularies the upload template names, so there is nothing to adopt or move
when the vocabularies change. This page explains where the files come from and what to do when a
test reports a change.

## Where the files come from

A concept scheme is published at its identifier with `.ttl` added. For
`https://w3id.org/ihfc-iugg/vocabularies/exploration-methods` the file is
`https://w3id.org/ihfc-iugg/vocabularies/exploration-methods.ttl`. The package downloads the file
the first time a field needs it and keeps it in a cache directory outside the repository:

- the `vocabularies` directory in the user cache directory for `ghfdb`, which
  [platformdirs](https://platformdirs.readthedocs.io) finds for the operating system
  (`~/.cache/ghfdb/vocabularies` on Linux)
- or the directory you pass to `ghfdb.vocabularies.caching_session()`

The downloads go through a caching HTTP session (`requests-cache`). The server's `ETag`,
`Last-Modified` and `Cache-Control` headers decide freshness, and no fixed expiry hides a change:

- Within the time the server allows (GitHub Pages sends `max-age=600`, ten minutes), the cached
  file is used without asking.
- After that the package asks the server whether the file changed. An unchanged file costs a
  `304` answer and is read from the cache, and a changed file is downloaded again.
- A file sent with none of these headers, such as the time scale download, cannot be checked.
  It is used for a day and downloaded again after that.
- When the server cannot be reached, the cached copy is used.
- A server error (502, 503 or 504) is tried again twice.

To refresh everything now, delete the cache directory.

### A scheme that is not published at its identifier

Lithology (`C25`) and stratigraphic age (`C26`) take their terms from vocabularies that are not
IHFC vocabularies and are not published as Turtle at their identifiers. The `vocabulary` object
of such a field names the file to download and its RDF format:

```json
"vocabulary": {
  "scheme": "http://resource.geosciml.org/classifierScheme/cgi/2016.01/simplelithology",
  "collection": null,
  "termForm": "localName",
  "download": "https://geosciml.org/resource/vocabulary/cgi/2016/simplelithology.rdf",
  "downloadFormat": "application/rdf+xml"
}
```

`downloadFormat` is `text/turtle` or `application/rdf+xml`. The file goes through the same
caching session and is cached in the same way. The term of a `localName` field is the last path
segment of the concept's URI, written without square brackets. A collection that holds other
collections gives the members of all of them. See
[ADR 0007](../adr/0007-lithology-and-age-take-terms-from-external-vocabularies.md) for why.

## What the tests do

The cache of a test session starts empty, in a temporary directory, so every test run and every
CI run reads the files as currently published. The tests fail on their own when the vocabularies
change in a way that matters here:

- A scheme or collection the schema links to is no longer defined in the file at its identifier,
  or in the file the field names to download. The failure names the field.
- A concept has no English preferred label.
- A template, a field reference page or another test depended on a term that moved or was removed.

## Respond to a change in the vocabularies

1. Run `uv run pytest` and read which fields the failures name.
2. If a scheme or collection was renamed, change the identifier in `ghfdb/fields/schema.json` by
   hand to the new one. If the address of a downloaded file moved, change `download` too.
3. If a term moved or was removed, fix what depended on it, and say so in the pull request:
   existing workbooks may no longer pass the check.
4. Add a line under `## [Unreleased]` in `CHANGELOG.md` when users of the package can see the
   difference.

See [ADR 0003](../adr/0003-vocabularies-are-read-from-their-permanent-identifiers.md) for why
the schema works this way and [the Python API](python-api.md) for the classes
involved.
