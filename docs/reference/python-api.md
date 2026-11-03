# Python API

## Field definitions

The names `ghfdb.fields` provides: `FieldSchema`, `Field`, `AllowedValue`,
`VocabularyBinding`, `VocabularyRelease` and `UnknownFieldError`. They read the packaged field
schema and need nothing beyond the standard library.

```{eval-rst}
.. automodule:: ghfdb.fields
   :members:
```

## Upload template

`ghfdb.template` provides `UploadTemplate`, which generates the upload template from the
field schema, and `TemplateError`, raised when a field cannot be written to it. The module
needs openpyxl, which `ghfdb` installs.

```{eval-rst}
.. automodule:: ghfdb.template
   :members:
```

## Adopting a vocabulary release

`ghfdb.fields.release`, with `ReleaseFiles`, `ReleaseMove`, `FieldChange`,
`MissingSchemeError` and `add_changed_line`, is the maintainers' tooling for moving the
field schema onto a newer release of the IHFC Controlled Vocabularies. Its `main` is the
command `python -m ghfdb.fields.release`. It needs the optional `vocabularies`
extra (`pip install "ghfdb[vocabularies]"`), which installs rdflib.

```{eval-rst}
.. automodule:: ghfdb.fields.release
   :members:
```
