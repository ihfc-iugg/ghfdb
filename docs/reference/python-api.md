# Python API

## Field definitions

The names `ghfdb.fields` provides: `load_schema`, `field_for_column`, `allowed_values`,
`AllowedValue`, `Vocabularies`, `caching_session` and `MissingSchemeError`. They read the
packaged field schema, which is a `frictionless.Schema`, and the vocabularies it links to.
`Vocabularies.releases` lists the releases of the vocabularies read so far, as the
identifiers the concept schemes say they are part of.

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

`Dataset.check` finds what is wrong with the children and returns the problems as a
DataFrame (see Checking the children below).

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

## Checking the children

`Dataset.check` and `ghfdb.qc.DatasetCheck` compare the children with the field schema.
`DatasetCheck(data, schema).problems()` takes any DataFrame whose columns are field codes
and returns one line for each problem, ordered by row and then by the field's place in the
schema. The columns are `PROBLEM_COLUMNS`: `row`, `code`, `column_name`, `kind`, `value` and
`suggestion`. The `row` is the index of the data, which is the Excel row for a dataset read
from a workbook. The `value` is the cell as it was found.

```python
from pathlib import Path

from ghfdb import Dataset

problems = Dataset.from_workbook(Path("my-heat-flow-data.xlsx")).check()
problems[problems["kind"] == "not in vocabulary"]
```

`Kind` names the kinds of problem. A field mandatory in both domains with no value is
`missing`. A cell that is not the field's type, or does not match its pattern, is
`wrong type`, and a number stored as text is accepted. A number below the minimum or above
the maximum, or text longer than the maximum length, is `out of range`; the range is checked
only on values of the right type. A value that is not one of the field's terms is `not in
vocabulary`, and carries the closest term as a `suggestion` when one is alike enough
(`DatasetCheck.suggestions`; `CLOSE_ENOUGH`, 0.8, is the least likeness it accepts). A field the data has no column for is one `no column` problem
with no row, and a mandatory one is also `missing` on every child. `unknown column` and
`duplicate column` come from `UploadWorkbook.column_problems`. When a field takes several
values in a cell, written with a separator, and has allowed values or a pattern, each value
is checked on its own and the problem names that value.

```{eval-rst}
.. automodule:: ghfdb.qc.check
   :members:
```
