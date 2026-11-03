# ghfdb

Python tools for working with the Global Heat Flow Database (GHFDB).

The first part of the package, `ghfdb.qc`, is quality control for GHFDB data template
workbooks: it checks a workbook against the field schema and the IHFC controlled
vocabularies, and scores each heat-flow determination with the GHFDB quality scheme.
It is in development and does not yet check or score anything.

```{toctree}
:maxdepth: 1
:caption: Maintainers

developer/brainstorm
contributing/standards/testing
contributing/standards/documentation
contributing/standards/code-documentation
contributing/standards/django
```
