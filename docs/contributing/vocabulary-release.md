# Adopt a new vocabulary release

The field schema names the release of the IHFC Controlled Vocabularies its allowed values come
from. The schema holds no term. The terms are read from the named release when the schema is
loaded, so adopting a newer release means changing the name of the release in the schema and
reading what the tests say. This page walks through it.

## Move the field definitions onto a release

1. Find the release's version, such as `2026.2`, and its DOI on the vocabularies' releases
   page, <https://github.com/ihfc-iugg/controlled-vocabularies/releases>.

2. In `ghfdb/fields/schema.json`, change `version` and `doi` under `vocabularyRelease`. Leave
   `repository` as it is.

3. Run the tests. The first run downloads the release into the cache directory.

   ```bash
   uv run pytest
   ```

   The test that compares the stated release with the newest published release passes again,
   and every test that fails names a field or a template cell that depends on a term that moved
   or was removed.

4. Build the documentation, which shows the new terms in the field reference, and look at the
   fields the failing tests named.

   ```bash
   uv run sphinx-build -W --keep-going -b html docs docs/_build/html
   ```

5. Add a line under `## [Unreleased]` and `### Changed` in `CHANGELOG.md` naming the old and
   the new release and their DOIs, and say in the pull request which terms were added, removed
   or renamed. A removed or renamed term can mean existing workbooks no longer pass the check.

6. Open the pull request.

## Where the release is kept

The first time the package needs a release, it downloads `vocabularies-full.zip` from that
release's page on GitHub and unpacks the Turtle files into `ghfdb/vocabularies/<version>` in the
user's cache directory (`$XDG_CACHE_HOME`, or `~/.cache`). `GHFDB_VOCABULARY_CACHE` names another
directory. The release is not stored in this repository. To fetch a release again, delete its
directory from the cache.

## When the release lacks a scheme

If a field names a scheme or collection that the release does not have, loading the schema
raises `MissingSchemeError` naming the field's code and the missing name. Either the vocabularies
renamed or dropped the scheme, in which case the field's `schemeName` or `collectionName` in the
schema needs a decision, or the download is incomplete and its directory should be deleted from
the cache.

## Why the schema holds no term

Allowed values are never typed in or copied. They come from the release, so that a term is
exactly the one the vocabularies publish, and a change in the vocabularies reaches this
package as a failing test and not as a surprise. See
[ADR 0003](../adr/0003-vocabularies-are-read-from-the-published-release.md) and
[the Python API](../reference/python-api.md) for the classes involved.
