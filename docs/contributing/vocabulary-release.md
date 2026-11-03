# Adopt a new vocabulary release

When the IHFC Controlled Vocabularies publish a new release, the allowed values of the
fields that take terms from them are moved onto it in one step. The step rewrites only the
scheme and collection addresses, `allowedValues`, `constraints.enum` and `vocabularyRelease`
of `src/ghfdb/fields/schema.json`, and adds a line to the changelog. A test then checks that
nothing was edited by hand. This page walks through the step.

## Move the field definitions onto a release

1. Download the release's Turtle files and its `LICENSE` from the vocabularies' repository
   and put them in `vocabularies/<version>/`, where `<version>` is the release's version,
   such as `2026.2`.

2. Install the optional extra that reads the files:

   ```bash
   uv sync --extra vocabularies
   ```

3. Run the command with the version and the directory:

   ```bash
   uv run python -m ghfdb.fields.release 2026.2 vocabularies/2026.2
   ```

   Run it from the repository root. It rewrites `src/ghfdb/fields/schema.json` and adds a line
   under `## [Unreleased]` and `### Changed` in `CHANGELOG.md`, naming the old and the new release
   and their DOIs. `--schema` and `--changelog` name other files.

4. Read the report. There is one line for every field that takes terms from a vocabulary:

   ```text
   C43: unchanged
   C44: added [new term]; removed [old term]; relabelled [Old name] -> [New name]
   ```

   A removed or relabelled term can mean existing workbooks no longer pass the check, so say so
   in the pull request when the report shows one.

5. Remove the old release's directory, `vocabularies/<old version>/`, so that only the stated
   release is kept.

6. Run the tests. `TestShippedSchemaDrift` compares every vocabulary field with the files in
   `vocabularies/<version>/` and names each field that differs.

   ```bash
   uv run pytest
   ```

7. Commit the new directory, the changed schema, the changelog and the removed directory, and
   open the pull request.

## When the release lacks a scheme

If a field names a scheme or collection that the release no longer has, the command prints the
field's code and the missing name, exits with status 1 and changes neither file. Either the
vocabularies renamed or dropped the scheme, in which case the field's `schemeName` or
`collectionName` in the schema needs a decision, or the download is incomplete.

## Why the file is regenerated

Allowed values are never typed in. They come from the release, so that a term is exactly the
one the vocabularies publish, and the drift test fails when a value was edited by hand or the
stated release does not match the files kept in `vocabularies/`. The field reference pages are
built from the same schema file, so they show the new terms the next time the documentation is
built. See [the Python API](../reference/python-api.md) for the classes the command uses.
