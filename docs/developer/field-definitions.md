# Field definitions

The package ships what the GHFDB upload template records about each of its 70 fields: the
field code and published column name, the title and meaning, the type, unit and range, the
obligation, the domain, how the field enters the quality score, and the allowed values of
every field that takes terms from a controlled vocabulary. Every fact names the source it was
taken from. The definitions are read from a file inside the package, so loading them needs no
network access.

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

The result is a {py:class}`~ghfdb.fields.FieldSchema`. Its `release` attribute says which
version of the IHFC Controlled Vocabularies the allowed values come from.

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
   field.vocabulary.scheme_name    # 'conductivity-methods'
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

Every public name is described on the [Python API](../reference/python-api.md) page.
