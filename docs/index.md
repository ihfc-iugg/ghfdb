# ghfdb

Python tools for working with the Global Heat Flow Database (GHFDB).

The first part of the package, `ghfdb.qc`, is quality control for GHFDB data template
workbooks: it checks a workbook against the field schema and the IHFC controlled
vocabularies, and scores each heat-flow determination with the GHFDB quality scheme.
It checks a workbook with the `ghfdb check` command (see
[Check a workbook](user-guide/check.md)). Scoring is still to come, but the scheme it will
implement is written down: the [quality scheme](reference/quality-scheme/index.md) states each
rule with its source, every departure from the paper, and the worked examples every
implementation must pass.

```{toctree}
:maxdepth: 1
:caption: User guide

user-guide/check
user-guide/field-definitions
```

```{toctree}
:maxdepth: 1
:caption: Reference

reference/fields/index
reference/rules
reference/quality-scheme/index
upload-template/index
```

```{toctree}
:maxdepth: 1
:caption: Maintainers

contributing/brainstorm
contributing/python-api
contributing/vocabularies
contributing/standards/testing
contributing/standards/documentation
contributing/standards/code-documentation
contributing/standards/django
adr/index
```
