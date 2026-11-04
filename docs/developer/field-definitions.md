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

1. Import `load_schema` and call it:

   ```python
   from ghfdb.fields import load_schema

   schema = load_schema()
   ```

2. Count or iterate the fields. They come in field-code order: `P1` to `P13`, `C1` to
   `C49`, then the assessment fields `A1` to `A8`.

   ```python
   len(schema.fields)                           # 70
   schema.field_names[:3]                       # ['P1', 'P2', 'P3']
   ```

The result is a [Frictionless Table Schema](https://framework.frictionlessdata.io/docs/framework/schema.html),
a `frictionless.Schema`, so everything Frictionless does with a schema works on it.

Each vocabulary field links to the permanent identifier of its concept scheme, such as
`https://w3id.org/ihfc-iugg/vocabularies/exploration-methods`. The scheme's file, at the
identifier with `.ttl` added, is downloaded into the `vocabularies` directory of the user cache
directory for `ghfdb` (`~/.cache/ghfdb/vocabularies` on Linux) the first time it is needed.
After that the server's `ETag` and `Cache-Control` decide whether the cached file is still
current, so a change in the vocabularies reaches you without a fixed delay, and a cached file is
used when you are offline. Delete the directory to refresh everything now.

The downloads use the session `ghfdb.fields.caching_session()` builds. To keep the files in
another directory, pass it in. To use your own session, for example one behind a proxy, pass it
to `Vocabularies`:

```python
from ghfdb.fields import Vocabularies, caching_session, load_schema

schema = load_schema(vocabularies=Vocabularies(caching_session(my_directory)))
schema = load_schema(vocabularies=Vocabularies(my_session))
```

The schema in memory has an `enum` constraint on every field that has allowed values. To get
it as a dictionary or a JSON file, call `schema.to_descriptor()` or `schema.to_json(path)`.

## Look a field up

1. Look a field up by its field code with `get_field`, or by the published column name with
   `field_for_column`. The column name keeps its casing.

   ```python
   from ghfdb.fields import field_for_column

   field = schema.get_field("C43")
   same = field_for_column(schema, "tc_method")
   assert field is same
   ```

2. Read the facts from the field you get back. The title, meaning, type and constraints are
   Frictionless properties. The facts Table Schema has no property for are in `field.custom`.

   ```python
   field.title                                  # 'Thermal conductivity method'
   field.custom["obligation"]                   # 'M'
   field.custom["domain"]                       # ['B', 'S']
   field.custom["columnName"]                   # 'tc_method'
   field.custom["vocabulary"]["scheme"]         # 'https://w3id.org/ihfc-iugg/vocabularies/conductivity-methods'
   field.constraints["enum"][0]                 # the first term, as written in a cell
   field.custom["sources"]["obligation"]        # 'upload-template'
   ```

A code the schema does not hold raises `frictionless.FrictionlessException`. A column name it does not
hold raises `KeyError`.

## Read the allowed values of a field

The `enum` constraint holds the terms of a field as written in a workbook cell. To get
more than the term, call {py:func}`~ghfdb.fields.allowed_values` with the field and the
vocabularies. It gives each value as an {py:class}`~ghfdb.fields.AllowedValue` with the term,
the concept's English label, its URI and its notation. A field with no list, such as a
free-text field, gives an empty tuple.

```python
from ghfdb.fields import Vocabularies, allowed_values

for value in allowed_values(schema.get_field("C44"), Vocabularies()):
    print(value.term, value.uri)
```

Every public name is described on the [Python API](../reference/python-api.md) page, and every
field is described in the [field reference](../reference/fields/index.md).
