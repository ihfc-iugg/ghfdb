# Python API

## Field definitions

The names `ghfdb.fields` provides: `Field`, `load_schema`, `field_for_column`, `allowed_values`,
`AllowedValue`, `Vocabularies`, `caching_session` and `MissingSchemeError`. They read the
packaged field schema, which is a `frictionless.Schema`, and the vocabularies it links to.
`Vocabularies.releases` lists the releases of the vocabularies read so far, as the
identifiers the concept schemes say they are part of.

```{eval-rst}
.. automodule:: ghfdb.fields
   :members:
```

### Naming a field in code

`Field` has one member for each field of the schema, named by the field's published column name
and valued by its code, so `Field.tc_location == "C42"`. Python source in ghfdb names a field
through `Field` and never writes a code. The data stays keyed by field code: `Dataset.data`, the
worked examples and the workbooks do not change, and a member is a string, so `data[Field.tc_location]`
reads the column `C42`.

`ghfdb/fields/names.py` is generated from `schema.json`. After the schema changes, write it again
with `python -m ghfdb.fields.generate`, which calls `FieldNames.write`. `FieldNames.render` makes
the source of the file from the schema's fields. A test fails while the file differs from what
the schema generates.

```{eval-rst}
.. automodule:: ghfdb.fields.generate
   :members:
```

### Reading the cells of a field

`ghfdb.fields.cells` holds the two readings that the check and the scoring share, so that both
read a cell the same way. `parse_numbers` reads text cells as numbers, empty where a cell is
empty, is not a number or is infinite. `terms_by_name` maps the local name of each allowed value
of a field to its term, and refuses a field in which two allowed values share a local name. `local_name` in
`ghfdb.fields.vocabularies` gives the local name of a concept URI, the last segment of its path.

```{eval-rst}
.. automodule:: ghfdb.fields.cells
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
the workbook's path, the problems, the number of children, the `Vocabularies` the check read and
the scores `Dataset.scores` returned for the children, indexed by Excel row, and whose `write`
method returns the report's path. `SCORE_TABLE` lists the columns of its table of preview scores:
each is a `ScoreColumn` of a heading, the column of the scores it shows and the page of the scheme
reference that explains it, so the order of that list orders headings, cells and links together.
The command, its report and each kind of problem are described in
[Check a workbook](../user-guide/check.md).

## Quality scores

`Dataset.scores` scores the children under the [quality scheme](../reference/quality-scheme/index.md)
and returns one row for each, indexed like `data`.

### The table of scores

The columns of the table are those of `ghfdb.qc.scores.SCORE_COLUMNS`:

* `rules` names the set of rules that scored the child, `probe sensing` or `borehole and mine`,
  and is `<NA>` when none did.
* `U`, `T`, `TC` and `M` are the U-score, the T-score, the TC-score and the M-score. A T-score
  or TC-score that is not determined is `<NA>` and never 0, and the grades are then `Ux` and `Mx`.
* `marked` says whether the M-score carries the missing-information mark.
* `flags` writes the seven perturbation flags, and `code` joins the U-score, the M-score and the
  flags by points, as in `U2.M1.SeXxV--`.
* The `own` columns are the scores of the child's own gradient and conductivity, before the
  corrections of the child apply, with their marks in `own_T_marked` and `own_TC_marked`.

Given the problems `Dataset.check` found, a cell a problem names is scored as empty, so the
child is scored as the report scores it. Without them, a value is scored as the scheme's pages
say. Like `Dataset.check`, `Dataset.scores` takes the `schema` to read the fields against, the
packaged one when none is given.

```python
from pathlib import Path

from ghfdb import Dataset

dataset = Dataset.from_workbook(Path("my-heat-flow-data.xlsx"))
scores = dataset.scores(dataset.check())
scores[["M", "code"]]
```

### Criteria and tables

Each criterion of the scheme is declared once, as a `Criterion` in `ghfdb.qc.probe` or
`ghfdb.qc.borehole`. A `Criterion` holds the identifier the worked examples use, such as
`probe-t.penetration`, a title, the paper's table and row it comes from, and the table that
gives its penalties. `ghfdb.qc.criteria.CRITERIA` lists every criterion by its identifier, and
the pages of the scheme render each criterion's penalty table from its declaration.

There are three kinds of table in `ghfdb.qc.penalties`, and each is a `Table`, which is what the
scoring and the pages ask of one: the fields it reads, the concepts it names, its largest penalty
and its `score` of every child.

* `Bands` score a number against ordered edges, each a `Band`. `Depths` are bands of a depth
  below sea level, read from the elevation of the site.
* `Classes` score a term against groups of concepts, each a `Group`.
* `Cases` score several fields together by rows of conditions, each a `Case`, the poorest row
  that holds counting.

The conditions of a row of cases, and the conditions that leave a band out, are `Conditions`: the
concepts each named field may hold.

Every table scores all the children at once and keeps the poorest of a child's values. A value
that is empty, or that fits no row, takes the largest penalty of its table, the lowest of its
rows, so a table declares only whether that sets the missing-information mark, with
`empty_marked` and `unmatched_marked`. A table of cases gives its empty outcome only to a
combination that no row holds, in which a field some row names is empty: a row holds whatever
the fields it does not name contain. The pages render each table from its attributes. A
criterion gives a `Penalty`, the penalty and the mark of each child, and a T-score or TC-score
is a `Score`, rounded to `SCORE_DECIMALS` places.

A declaration names a concept by its local name, the last segment of its URI, written as a
string under the field whose vocabulary holds it: `"probePulse"` under `Field.tc_method`. The
field already says which vocabulary the name belongs to, so a name is never qualified. A group
that two criteria share is a tuple of names in the module that owns it, and one used once is
written where it is used. `Scores.concepts` collects the concepts the declarations name, and
`ghfdb.qc.criteria.term_names` resolves them to the term each field accepts in the vocabularies
as published, raising `MissingSchemeError` naming the field and the name when the field has no
such value, for instance when a name is misspelt or the vocabulary renames the concept.
`ghfdb.qc.inputs.Inputs` reads a scored field of a table of children the first time it is
asked: numbers as numbers, terms as concept names, and a value that is neither as empty. A cell holding a Python list holds several values. The term lookup
and the number parser that `ghfdb.qc.check` uses are in `ghfdb.fields.cells`, and the scoring
uses the same ones.

### The rule classes

A set of rules is a `ghfdb.qc.ruleset.RuleSet`, which declares its `criteria`, and where it has
them its `waivers`, `stand_ins`, `conditions` and `extra_fields`, as class attributes. The fields
it reads and the concepts it names follow from those declarations, and so do the penalties of its
criteria for a child and for a measurement on its own, as the `RuleScores` of its T-score,
TC-score and their own scores. `ghfdb.qc.probe.ProbeRules` scores the
T-score and the TC-score from its two lists, and its waivers are the two corrections that leave
the water depth or the tilt out of a child's T-score. `ghfdb.qc.borehole.BoreholeRules` scores
the TC-score from its list, with the plain pT conditions standing in for their agreement with the
in-situ correction in a measurement's own score, chooses which of the three cases a gradient is
and applies the interval depth gate. `ghfdb.qc.uncertainty.UScore` grades the uncertainty.
`ghfdb.qc.scores.Scores` routes each child to its rules once, hands each set of rules the
children it scores, writes the perturbation flags, grades the M-score and assembles the table of
scores.

### Change or add a criterion

To change one penalty, one group of concepts or one edge, edit that one declaration. The
scheme's page shows the new value, and the worked example that scores it says whether the paper
agrees.

To add a criterion:

1. Write its `Criterion` in `ghfdb.qc.probe` or `ghfdb.qc.borehole`, with an identifier of the
   form `<rules>-<t or tc>.<name>` that is never reused, a title, the paper's table and row as
   `source`, and a `Bands`, `Classes` or `Cases` table over the `Field` members it reads. Name a
   concept by its local name, as a string under the field it belongs to.
2. Add it to that module's `T_CRITERIA` or `TC_CRITERIA`. The rules score every criterion of the
   list they score from, and the fields the rules read and the concepts the scheme names are
   collected from the lists, so nothing else lists them. Two things are declared beside the
   lists, in the class of the rules: a correction that waives a criterion for a child that has
   it goes in `waivers`, by the criterion's identifier, and a criterion that replaces another in
   a measurement's own score goes in `stand_ins`. The three criteria of the borehole T-score are
   the three cases of a gradient and not a sum, so a new one is also chosen between in
   `BoreholeRules.temperature_methods`.
3. Add the criterion's identifier and a statement of it to `criteria` in
   `ghfdb/qc/worked_examples.json`, and a worked example that scores it, naming the criterion in
   its own `criteria`. A test fails while a declared criterion has no example, or an example
   names one that is not declared.
4. Show it on the page of the scheme that explains it, with the `criterion` call that the other
   criteria use on that page.
5. If a table cannot say part of it, put that part in the rule class and describe it on the
   page in words.

A condition on a whole set of rules, such as the gate that stops the scoring of every other
criterion, is code in the rule class and is not a `Criterion`.

```{eval-rst}
.. automodule:: ghfdb.qc.inputs
   :members:

.. automodule:: ghfdb.qc.penalties
   :members:

.. automodule:: ghfdb.qc.criteria
   :members:

.. automodule:: ghfdb.qc.ruleset
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
