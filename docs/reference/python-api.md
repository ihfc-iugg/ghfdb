# Python API

## Field definitions

The names `ghfdb.fields` provides: `load_schema`, `field_for_column`, `allowed_values`,
`AllowedValue`, `Vocabularies`, `caching_session` and `MissingSchemeError`. They read the
packaged field schema, which is a `frictionless.Schema`, and the vocabularies it links to.

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
