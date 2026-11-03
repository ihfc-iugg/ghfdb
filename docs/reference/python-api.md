# Python API

## Field definitions

The names `ghfdb.fields` provides: `FieldSchema`, `Field`, `AllowedValue`,
`VocabularyBinding`, `VocabularyRelease` and `UnknownFieldError`. They read the packaged field
schema and need nothing beyond the standard library.

```{eval-rst}
.. automodule:: ghfdb.fields
   :members:
```

## Adopting a vocabulary release

`ghfdb.fields.release`, with `ReleaseFiles`, `ReleaseMove`, `FieldChange` and `MissingSchemeError`, is the
maintainers' tooling for moving the field schema onto a
newer release of the IHFC Controlled Vocabularies. It needs the optional `vocabularies`
extra (`pip install "ghfdb[vocabularies]"`), which installs rdflib.

```{eval-rst}
.. automodule:: ghfdb.fields.release
   :members:
```
