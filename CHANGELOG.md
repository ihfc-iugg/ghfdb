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
  source. `FieldSchema.load()` reads them from a file shipped in the package, and a field is
  looked up by its code or its published column name.
- The allowed values of the 25 fields that take terms from a controlled vocabulary, read
  from release 2026.1 of the IHFC Controlled Vocabularies when the field definitions are
  loaded. The field schema names the release and, for each of these fields, the concept
  scheme and collection, and holds no term. The release is downloaded from its GitHub release
  the first time it is needed and kept in a cache directory (`GHFDB_VOCABULARY_CACHE` changes
  where). `FieldSchema.descriptor()` builds the complete Frictionless Table Schema, with the
  allowed values as `enum`, in memory.
- `ghfdb.fields.release`, which downloads and reads a vocabulary release. A test fails when the
  vocabularies have published a release newer than the one the field schema states.
- `ghfdb.template.UploadTemplate`, which generates the upload template from the field schema
  (the three sheets, description rows and choice lists) and writes it to a path without
  replacing an existing file unless asked.
- The documentation site publishes the upload template generated for its version, with a
  list of how it differs from the hand-maintained template.
- Documentation: a developer guide for loading and looking up field definitions, and a Python
  API reference.

### Changed

- openpyxl is now a runtime dependency, because `ghfdb.template` writes the upload template.
