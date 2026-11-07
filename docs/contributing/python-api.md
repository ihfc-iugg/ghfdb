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
schema. The columns are `PROBLEM_COLUMNS`: `row`, `code`, `column_name`, `kind`, `value`,
`suggestion`, `rule` and `related`. The `row` is the index of the data, which is the Excel
row for a dataset read from a workbook. The `value` is the cell as it was found.

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
`duplicate column` come from `UploadWorkbook.column_problems`. An unknown column carries as its
`suggestion` the published column name it is closest to, when one is at least `CLOSE_ENOUGH`
alike, so a misspelled header such as `Ref_ISGN` names `Ref_IGSN`. When a field takes several
values in a cell, written with a separator, and has allowed values or a pattern, each value
is checked on its own and the problem names that value.

```{eval-rst}
.. automodule:: ghfdb.qc.check
   :members:
```

## Cross-field rules

`ghfdb.qc.rules` declares the rules that relate several fields of a child. Every rule is a
`Rule`. A `RequiredWhen` rule requires the fields mandatory in one `Domain` for the children of
that domain, and an `AllowedWhen` rule limits one field once another holds the concepts of a
`Condition`. `RULES` holds
them, and `DatasetCheck(data, schema, rules, vocabularies)` applies the rules it is given
after the field check. A broken rule is a `rule` line, with the rule's identifier in the
`rule` column and the field that decided the rule applies in the `related` column. The
module documentation below says how to add a rule of a new kind.

```{eval-rst}
.. automodule:: ghfdb.qc.rules
   :members:
```

The report the `ghfdb check` command writes is built by `ghfdb.qc.report.Report`, which takes
the workbook's path, the problems, the number of children and the `Vocabularies` the check read,
and whose `write` method returns the report's path. The command, its report and each kind of
problem are described in [Check a workbook](../user-guide/check.md).

## Quality scores

The quality scheme is computed by four classes, one for each part the
[quality scheme](../reference/quality-scheme/index.md) separates. `ghfdb.qc.scheme.Terms`
resolves every concept the scheme names, by its URI, to the term its field accepts in the
vocabularies as published, and raises `MissingSchemeError` naming the concept when one is no
longer published. `ghfdb.qc.scheme.Inputs` reads the scored fields of a table of children once:
numbers as numbers, terms as concept URIs, and a value that is neither as empty. A cell holding a
Python list holds several values. Every criterion returns a `Penalty`, the penalty and the
mark of each child, and a T-score or TC-score is a `Score`. `ghfdb.qc.uncertainty.UScore` grades the uncertainty, and
`ghfdb.qc.scores.Scores` routes each child to its rules and writes its perturbation flags.
`ghfdb.qc.probe.ProbeRules` scores the children explored by probing, one method for each
criterion of the probe-sensing rules. `ghfdb.qc.borehole.BoreholeRules` scores the children
explored by drilling, mining and indirect methods in the same way, with one method for each
criterion of the borehole and mine rules, whose groups of concepts are lists of `Groups`: a
penalty and the concepts that earn it. Each works on every child at once. Both sets of rules
share the functions of `ghfdb.qc.scheme` that keep the `poorest` of a child's values, pair the
values of several fields (`combinations`), score `bands` of numbers or a list of `cases`, and
add the criteria into one score (`total`).

```{eval-rst}
.. automodule:: ghfdb.qc.scheme
   :members:

.. automodule:: ghfdb.qc.uncertainty
   :members:

.. automodule:: ghfdb.qc.probe
   :members:

.. automodule:: ghfdb.qc.borehole
   :members:

.. automodule:: ghfdb.qc.scores
   :members:
```
