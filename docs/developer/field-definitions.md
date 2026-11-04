# Field definitions

The package ships what the GHFDB upload template records about each of its 70 fields: the
field code and published column name, the title and meaning, the type, unit and range, the
obligation, the domain, how the field enters the quality score, and the allowed values of
every field that takes terms from a controlled vocabulary. Every fact names the source it was
taken from. The definitions are read from a file inside the package. The allowed values of the
vocabulary fields are read from the IHFC Controlled Vocabularies that the file links to. Their
files are downloaded the first time you load the definitions and kept in a cache directory
after that, so only the first load needs network access.

## Load the field definitions

1. Import `FieldSchema` and call `load`:

   ```python
   from ghfdb.fields import FieldSchema

   schema = FieldSchema.load()
   ```

2. Count or iterate the fields. They come in field-code order: `P1` to `P13`, `C1` to
   `C49`, then the assessment fields `A1` to `A8`.

   ```python
   len(schema)                                  # 70
   [field.code for field in schema][:3]         # ['P1', 'P2', 'P3']
   ```

The result is a {py:class}`~ghfdb.fields.FieldSchema`.

Each vocabulary field links to the permanent identifier of its concept scheme, such as
`https://w3id.org/ihfc-iugg/vocabularies/exploration-methods`. The scheme's file, at the
identifier with `.ttl` added, is downloaded into `~/.cache/ghfdb/vocabularies` (or
`$XDG_CACHE_HOME/ghfdb/vocabularies`) the first time it is needed. After that the server's
`ETag` and `Cache-Control` decide whether the cached file is still current, so a change in the
vocabularies reaches you without a fixed delay, and a cached file is used when you are offline. Set `GHFDB_VOCABULARY_CACHE` to keep the downloads in another directory, and
delete the directory to refresh everything now. Call
`ghfdb.fields.vocabularies.cache_directory()` to see which directory is in use.

The downloads use the session `ghfdb.fields.vocabularies.caching_session()` builds. To use
your own session, for example one behind a proxy, pass it in:

```python
from ghfdb.fields import FieldSchema, Vocabularies

schema = FieldSchema.load(vocabularies=Vocabularies(my_session))
```

To get the whole schema as a Frictionless Table Schema, with an `enum` on every field that
has allowed values, call `schema.descriptor()`. It builds the dictionary on each call.

## Look a field up

1. Index the schema with a field code or with the published column name. The column name
   keeps its casing.

   ```python
   field = schema["C43"]
   same = schema["tc_method"]
   assert field is same
   ```

2. Read the facts from the {py:class}`~ghfdb.fields.Field` you get back.

   ```python
   field.name                      # 'Thermal conductivity method'
   field.obligation                # 'M'
   field.domain                    # ('B', 'S')
   field.vocabulary.scheme  # 'https://w3id.org/ihfc-iugg/vocabularies/conductivity-methods'
   field.allowed_values[0].term    # the first term, as written in a cell
   field.sources["obligation"]     # 'upload-template'
   ```

A code or column name the schema does not hold raises
{py:class}`~ghfdb.fields.UnknownFieldError`.

## Read the allowed values of a field

A field that takes terms from a controlled vocabulary lists them in `allowed_values`, each an
{py:class}`~ghfdb.fields.AllowedValue` with the term as written in a workbook cell, the
concept's English label and its URI. A field with no list, such as a free-text field, has an
empty tuple.

```python
for value in schema["C44"].allowed_values:
    print(value.term, value.uri)
```

Every public name is described on the [Python API](../reference/python-api.md) page, and every
field is described in the [field reference](../reference/fields/index.md).
