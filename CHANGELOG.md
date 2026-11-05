# Changelog

All notable changes to this project are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the package follows
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- The `ghfdb` package, with an empty `ghfdb.qc` subpackage for quality control.
- `ghfdb.fields`, which describes the 70 fields of the upload template (`P1`-`P13`,
  `C1`-`C49` and the assessment fields `A1`-`A8`): published column name, meaning, type,
  unit, range, obligation, domain, quality relevance and allowed values, each fact with its
  source. `load_schema()` reads them from a file shipped in the package with Frictionless
  and returns a `frictionless.Schema`. A field is looked up by its code with `get_field`, and by
  its published column name with `field_for_column()`. The facts Table Schema has no property for
  are in each field's `custom` dictionary.
- The allowed values of the 25 fields that take terms from a controlled vocabulary, read
  from the IHFC Controlled Vocabularies as currently published when the field definitions are
  loaded. The field schema links each of these fields to the permanent identifier of its
  concept scheme and, where it narrows the choice, its collection, and holds no term and no
  version. Each scheme's file is downloaded from its identifier the first time it is needed and
  downloaded again only when the server says it changed. The cache is in the user cache
  directory (`caching_session()` takes another). `frictionless`, `platformdirs`, `requests` and
  `requests-cache` are now runtime dependencies. The loaded schema is the complete Frictionless
  Table Schema, with the allowed values as `enum`, in memory.
- `ghfdb.fields.Vocabularies`, which downloads and reads the vocabulary files, and
  `allowed_values()`, which gives a field's values with the label and URI of each concept. The tests read
  the files as currently published, so they fail when the vocabularies change.
- `ghfdb.template.UploadTemplate`, which generates the upload template from the field schema
  (the three sheets, description rows and choice lists) and writes it to a path without
  replacing an existing file unless asked.
- The documentation site publishes the upload template generated for its version, with a
  list of how it differs from the hand-maintained template.
- Documentation: a developer guide for loading and looking up field definitions, and a Python
  API reference.
- The `ghfdb check <workbook>` command, which checks the `data list` sheet of a filled-in upload
  template against the field schema and the published vocabularies and writes
  `<name>.report.html` beside the workbook, a single web page with a summary and a table of
  problems. It
  gives status 0 for no problem, 1 for problems and 2 when it could not run. `ghfdb.qc.report.Report`
  writes the report, and `ghfdb.cli.main` and `ghfdb.cli.run` run the command.
- `ghfdb.Dataset`, the children of a workbook as one pandas table, with `Dataset.from_workbook`
  and `Dataset.check`. `fastexcel`, `pandas`, `pyarrow` and `jinja2` are now runtime
  dependencies.

- Cross-field rules, which relate several fields of one child. `ghfdb check` and
  `Dataset.check` apply them after the field check, and a child that breaks one gets a
  problem of the new kind `rule`. The report shows the rule's identifier linked to its entry
  in the published reference, its statement and the field that made it apply.
  `ghfdb.qc.rules` declares the rules.

### Changed

- The problem table has two new columns, `rule` and `related`, after `suggestion`. They are
  set for a `rule` problem only. `Dataset.check` takes the rules to apply, which default to
  all of them.
- openpyxl is now a runtime dependency, because `ghfdb.template` writes the upload template.
- The documentation build now checks that every concept, scheme and collection address in the
  field reference is an `http` or `https` address and encodes the brackets and parentheses that
  could end a Markdown link. An address that is anything else stops the build with a message
  naming it. The check uses the `validators` package, a new documentation dependency.
- The documentation loads mermaid 11.12.1 as a single script with a subresource integrity hash,
  so a browser refuses the file if the CDN serves anything other than the published build. It
  was loaded without one before. The diagrams are drawn as before. `docs/conf.py` holds the
  version and hash, with the command that produces a new hash for an upgrade.

### Scheme changes

- Added rule CF-1: a child explored by drilling, clustered drilling, mining, tunneling or
  indirect estimation has every field mandatory for borehole and mine data only filled
  (`C5`, `C31`, `C32`).
- Added rule CF-2: a child explored by probing, onshore, offshore or clustered, has every field
  mandatory for probe sensing only filled (`C6`, `C23`).
- Added rule CF-3: a thermal conductivity location of literature or unspecified (`C42`) is
  allowed only when the thermal conductivity source (`C41`) is assumed from literature.
- A field mandatory in one domain only is no longer left unchecked: when it is empty for a
  child of that domain, it is reported as a `rule` problem.
