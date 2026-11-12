# Python API

## What is public

These are public. Their names and behaviour change only with a release and a line in the
changelog:

* `ghfdb.Dataset`, and `ghfdb.template`, which writes the upload template.
* `ghfdb.fields`, which describes the fields.
* `ghfdb.vocabularies`, which reads the controlled vocabularies and names their concepts.
* `ghfdb.qc`, with the names it exports: `UploadWorkbook`, `CheckError`, `DatasetCheck` and
  `Kind`.
* `ghfdb.qc.rules`, which declares the cross-field rules.
* `ghfdb.qc.scheme`, which declares the quality scheme.

`ghfdb.qc.check`, `ghfdb.qc.workbook`, `ghfdb.qc.report` and `ghfdb.qc.scores` are the entry
points that `Dataset` and the command line use. `ghfdb.qc.engine` is internal: it holds how
the declarations are evaluated, nothing outside `ghfdb.qc` imports it, and it changes without
notice. It is documented below for those who add a kind of rule or of table.

```text
ghfdb/
  dataset.py        Dataset
  vocabularies.py   Vocabularies, and concepts, which names a concept
  template.py       UploadTemplate
  fields/           the field schema and Field
  qc/
    check.py  workbook.py  report.py  scores.py
    rules.py        the cross-field rules CF-1 to CF-4
    scheme/         what the quality scheme says: domains, criteria, grades
    engine/         how the declarations are evaluated (internal)
```

## Field definitions

The names `ghfdb.fields` provides: `Field`, `load_schema`, `field_for_column` and
`allowed_values`. They read the packaged field schema, which is a `frictionless.Schema`, and
the vocabularies it links to.

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
with `uv run python scripts/generate_field_names.py`, which calls `FieldNames.write`.
`FieldNames.render` makes the source of the file from the schema's fields. A test fails while the
file differs from what the schema generates. The script is a developer tool and is not part of the
installed package.

## Vocabularies

`ghfdb.vocabularies` provides `Vocabularies`, which downloads and reads the vocabulary files,
`AllowedValue`, `MissingSchemeError`, `caching_session`, `local_name` and `concepts`.
`Vocabularies.releases` lists the releases of the vocabularies read so far, as the identifiers
the concept schemes say they are part of.

```{eval-rst}
.. automodule:: ghfdb.vocabularies
   :members:
```

### Naming a concept in code

`concepts` has one namespace for each field that draws on a vocabulary, named by the field's
published column name: the namespace of the field's concept scheme. A concept is an attribute
of it, or an item when its local name is not a Python name, and is an `rdflib.URIRef`:

```python
from ghfdb.vocabularies import concepts

concepts.tc_method.pointSource  # .../conductivity-methods/pointSource
concepts.tc_source["insitu-probe"]  # .../conductivity-sources/insitu-probe
concepts.tc_method.laboratory  # a collection of the same scheme
```

A collection that the vocabulary publishes is named the same way and stands for its members.
`concepts` is built from the packaged field schema alone, so naming a concept never touches the
network. A column name the schema lacks, or a field without a vocabulary, raises
`AttributeError` naming it.

Declarations name concepts and never terms. `ghfdb.fields.schema.FieldConcepts.resolve` is the
one place that turns what declarations name into what a field accepts: for each field, the term
of each concept it accepts, and the members of each collection named. It refuses a reference that
is neither an allowed value of its field nor a collection of the field's scheme, with a
`MissingSchemeError` naming the field and the reference. The check, the scoring and the
documentation all resolve through it.

```{eval-rst}
.. autoclass:: ghfdb.fields.schema.FieldConcepts
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

`ghfdb.qc.rules` declares the rules that relate several fields of a child: `CF_1` to `CF_4`,
listed in `RULES`. `DatasetCheck(data, schema, rules, vocabularies)` applies the rules it is given
after the field check. A broken rule is a `rule` line, with the rule's identifier in the
`rule` column and the field that decided the rule applies in the `related` column. A rule names
the vocabulary values it needs as concepts, and `DatasetCheck` resolves them to the terms the
field accepts.

```{eval-rst}
.. automodule:: ghfdb.qc.rules
   :members:
```

Every rule is a `Rule`. A `RequiredWhen` rule requires the fields mandatory in one `Domain` for
the children of that domain, and an `AllowedWhen` rule limits one field once another holds the
concepts of a `Condition`. They are in `ghfdb.qc.engine.rule_kinds`, whose documentation says how
to add a rule of a new kind.

```{eval-rst}
.. automodule:: ghfdb.qc.engine.rule_kinds
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

* `rules` names the scoring that scored the child, `probe sensing` or `borehole and mine`,
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

`ghfdb.qc.scores.Scores` routes each child to the scoring of its domain once, hands each scoring
the children it scores, writes the perturbation flags, grades the M-score and assembles the table
of scores.

```{eval-rst}
.. automodule:: ghfdb.qc.scores
   :members:
```

### What the scheme declares

`ghfdb.qc.scheme` declares the quality scheme, and the declarations come first in each of its
modules:

* `ghfdb.qc.scheme.domains` holds the two domains, `BOREHOLE` and `PROBE_SENSING`. Each is the
  collection of exploration methods that the vocabulary publishes.
* `ghfdb.qc.scheme.probe` and `ghfdb.qc.scheme.borehole` hold the criteria of the two domains.
  Each criterion is a `Criterion`: the identifier the worked examples use, such as
  `probe-t.penetration`, a title, the paper's table and row it comes from, and the table that gives
  its penalties. The class that follows the criteria, `ProbeSensing` or `BoreholeAndMine`, is the
  scoring of its domain.
* `ghfdb.qc.scheme.groups` holds the groups of concepts that both domains name.
* `ghfdb.qc.scheme.grades` holds the U-score, the classes of the M-score and the perturbation
  flags.
* `ghfdb.qc.scheme.CRITERIA` lists every criterion by its identifier, and the pages of the scheme
  render each criterion's penalty table from its declaration.

A declaration names a concept as a reference, `concepts.tc_method.probePulse`, under the field
whose vocabulary holds it: `Field.tc_method`. A group that two criteria share is a tuple of
references in `ghfdb.qc.scheme.groups`, and one used once is written where it is used. A group
that the vocabulary publishes as a collection is the collection. `Scores.concepts` collects the
concepts the declarations name, and `FieldConcepts.resolve` resolves them to the term each field
accepts in the vocabularies as published, raising `MissingSchemeError` naming the field and the
reference when the field has no such value, for instance when the vocabulary renames the concept.

```{eval-rst}
.. automodule:: ghfdb.qc.scheme
   :members:

.. automodule:: ghfdb.qc.scheme.domains
   :members:

.. automodule:: ghfdb.qc.scheme.probe
   :members:

.. automodule:: ghfdb.qc.scheme.borehole
   :members:

.. automodule:: ghfdb.qc.scheme.grades
   :members:
```

### How the declarations are evaluated

`ghfdb.qc.engine` is internal. There are three kinds of table in `ghfdb.qc.engine.tables`, and
each is a `Table`, which is what the scoring and the pages ask of one: the fields it reads, the
concepts it names, its largest penalty and its `score` of every child.

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

`ghfdb.qc.engine.inputs.Inputs` reads a scored field of a table of children the first time it is
asked: numbers as numbers, vocabulary fields as concept URIs, and a value that is neither as
empty. A cell holding a Python list holds several values. `parse_numbers`, the number parser that
`ghfdb.qc.check` uses too, is in the same module, so that the check and the scoring read a
number the same way.

The scoring of a domain is a `ghfdb.qc.engine.domain.DomainScoring`, which declares its `criteria`,
and where it has them its `waivers`, `stand_ins`, `conditions` and `extra_fields`, as class
attributes. The fields it reads and the concepts it names follow from those declarations, and so
do the penalties of its criteria for a child and for a measurement on its own, as the
`DomainScores` of its T-score, TC-score and their own scores. `ProbeSensing` scores the T-score
and the TC-score from its two lists, and its waivers are the two corrections that leave the water
depth or the tilt out of a child's T-score. `BoreholeAndMine` scores the TC-score from its list,
with the plain pT conditions standing in for their agreement with the in-situ correction in a
measurement's own score, chooses which of the three cases a gradient is and applies the interval
depth gate. `ghfdb.qc.scheme.grades.UScore` grades the uncertainty.

### Change or add a criterion

To change one penalty, one group of concepts or one edge, edit that one declaration. The
scheme's page shows the new value, and the worked example that scores it says whether the paper
agrees.

To add a criterion:

1. Write its `Criterion` in `ghfdb.qc.scheme.probe` or `ghfdb.qc.scheme.borehole`, with an
   identifier of the form `<domain>-<t or tc>.<name>` that is never reused, a title, the paper's
   table and row as `source`, and a `Bands`, `Classes` or `Cases` table over the `Field` members
   it reads. Name a concept by its reference, under the field it belongs to.
2. Add it to that module's `T_CRITERIA` or `TC_CRITERIA`. The scoring scores every criterion of
   the list it scores from, and the fields it reads and the concepts the scheme names are
   collected from the lists, so nothing else lists them. Two things are declared beside the
   lists, in the class of the scoring: a correction that waives a criterion for a child that has
   it goes in `waivers`, by the criterion's identifier, and a criterion that replaces another in
   a measurement's own score goes in `stand_ins`. The three criteria of the borehole T-score are
   the three cases of a gradient and not a sum, so a new one is also chosen between in
   `BoreholeAndMine.temperature_methods`.
3. Add the criterion's identifier and a statement of it to `criteria` in
   `ghfdb/qc/worked_examples.json`, and a worked example that scores it, naming the criterion in
   its own `criteria`. A test fails while a declared criterion has no example, or an example
   names one that is not declared.
4. Show it on the page of the scheme that explains it, with the `criterion` call that the other
   criteria use on that page.
5. If a table cannot say part of it, put that part in the class of the scoring and describe it on
   the page in words.

A condition on a whole domain, such as the gate that stops the scoring of every other criterion,
is code in the class of the scoring and is not a `Criterion`.

```{eval-rst}
.. automodule:: ghfdb.qc.engine
   :members:

.. automodule:: ghfdb.qc.engine.inputs
   :members:

.. automodule:: ghfdb.qc.engine.tables
   :members:

.. automodule:: ghfdb.qc.engine.domain
   :members:
```
