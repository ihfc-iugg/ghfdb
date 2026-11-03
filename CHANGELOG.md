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
- The allowed values of the 25 fields that take terms from a controlled vocabulary, taken
  from release 2026.1 of the IHFC Controlled Vocabularies.
- `ghfdb.fields.release`, for maintainers, behind the optional `vocabularies` extra: it
  reads a vocabulary release and rewrites the allowed values of the field definitions from it.
- Documentation: a developer guide for loading and looking up field definitions, and a Python
  API reference.
