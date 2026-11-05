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

## Datasets

`ghfdb.Dataset` holds the children of a heat-flow dataset as one pandas DataFrame, `data`,
with one row per child and one column per field, named by field code. Read a dataset from a
filled-in upload template with `Dataset.from_workbook`. The index of `data` is the Excel row
of each child, so a row in the table is the row in the workbook.

```python
from pathlib import Path

from ghfdb import Dataset

dataset = Dataset.from_workbook(Path("my-heat-flow-data.xlsx"))
dataset.data.index  # the Excel row of each child
dataset.data["P1"]  # the heat-flow value of each child, as text
```

Every value is read as the text in its cell, and a cell of spaces only is missing. A formula
is read as the value Excel last saved for it and is never calculated.

```{eval-rst}
.. autoclass:: ghfdb.Dataset
   :members:
```

## Checking a workbook

`ghfdb.qc` provides `UploadWorkbook`, which reads the `data list` sheet of an upload
template workbook, and `CheckError`, raised when a workbook cannot be read. The header row
is found by its field codes, published column names or earlier column names, and the
description rows under it are skipped by their labels.

```{eval-rst}
.. automodule:: ghfdb.qc.workbook
   :members:
```
