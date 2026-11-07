# Check a workbook

The `ghfdb check` command compares a filled-in upload template workbook with the field
schema and the published vocabularies, and writes what it found to a report beside the
workbook. The report also gives every child its preview scores under the
[quality scheme](../reference/quality-scheme/index.md). This page describes the command, the
report it writes and each kind of problem. The workbook is read and never changed.

## Command

```text
ghfdb check <workbook>
```

| Argument | Meaning |
|---|---|
| `workbook` | The path of an `.xlsx` or `.xlsm` file with a sheet named `data list`. |

The command writes `<name>.report.html` in the folder of the workbook, replacing a report from
an earlier check, and prints one line on standard output:

```text
212 children, 37 problems in 14 of them, report: /data/my-data.report.html
```

The first time it runs, the command downloads the vocabularies and keeps them in the user's
cache directory. Later checks use the cache and need no network connection.

The exit status says what happened.

| Status | Meaning |
|---|---|
| `0` | The check ran and found no problem. |
| `1` | The check ran and found at least one problem. |
| `2` | The check could not run, and the reason is on standard error. The workbook is not a workbook or has no `data list` sheet or header row, the report cannot be written, the vocabularies are neither cached nor downloadable, or a rule names a concept the vocabularies no longer publish (the message names the rule). |

`ghfdb.cli.main` runs the command from Python and returns the status. `ghfdb.cli.run` is the
entry point the `ghfdb` command calls, and exits with that status.

## How a check runs

```{mermaid}
flowchart TD
    workbook["Workbook"] --> read["Read the data list sheet"]
    read --> columns["Match each column to a field"]
    columns --> cells["Check every cell against its field"]
    vocabularies["Published vocabularies"] --> cells
    cells --> rules["Check the cross-field rules"]
    columns --> layout["List the column problems"]
    rules --> scores["Score every child, leaving out the cells with a problem"]
    scores --> report["Write the HTML report beside the workbook"]
    layout --> report
    report --> status["Print one line and give a status"]
```

## The report

`ghfdb.qc.report.Report` writes the report as one web page that opens in any browser. The
page holds a summary, a table of the problems and a table of the preview scores, and no copy
of the data. Its styles are
in the page, and it has no script and no link to another file. It is written to a temporary file in the workbook's folder and moved over
the earlier report, so a check that fails leaves the earlier report whole.

### The problems table

One row for each problem. Problems of the workbook's columns come first, and the rest follow
in order of row and then of the field's place in the schema. The problems of the rules
follow the field problems of their row. `Dataset.check` gives the same table, with the columns
named `row`, `code`, `column_name`, `kind`, `value`, `suggestion`, `rule` and `related`.

| Column | Contents |
|---|---|
| Excel row | The row of the child in the workbook. Empty for a problem of the columns. |
| Field code | The code of the field, such as `P1`. Empty for an unknown column. |
| Published column name | The name the field's column has in the upload template. For an unknown column, its header. |
| Kind | The kind of problem (see below). |
| Value | The cell as it was found, written as text. The page shows markup in a value as text and never runs it. |
| Suggestion | The closest allowed term, for a value that is not in the vocabulary and is like one. |
| Rule | For a `rule` problem, the identifier of the broken rule, such as `CF-1`, linked to the rule in the latest published reference, with the rule's statement. Empty for every other kind. |
| Related | For a `rule` problem, the field that made the rule apply: its code, its published column name and the value found, such as `P12 explo_method [Drilling]`. Empty for every other kind. |

### The Preview scores table

One row for each child, after the problems, in the order of the workbook. Every score is a
preview: the GHFDB portal recalculates each one, and its value is authoritative. Each heading
of a score links to the page of the quality scheme that explains it. `Dataset.scores` gives the
same table.

| Column | Contents |
|---|---|
| Excel row | The row of the child in the workbook. |
| Rules | The rules that score the child, [probe sensing or borehole and mine](../reference/quality-scheme/index.md). Empty when no rules apply. |
| U-score | The [U-score](../reference/quality-scheme/u-score.md), `U1` to `U4`, or `Ux`. |
| T-score | The T-score, a number, from the [probe-sensing](../reference/quality-scheme/probe-sensing.md) or [borehole and mine](../reference/quality-scheme/borehole-and-mine.md) rules. |
| TC-score | The TC-score, a number, from the same rules. |
| M-score | The [M-score](../reference/quality-scheme/m-score.md), `M1` to `M4`, with an `x` when information is missing, or `Mx`. |
| Perturbation flags | The [perturbation flags](../reference/quality-scheme/perturbation-flags.md). |
| Quality code | The U-score, M-score and flags joined by full stops, as in `U2.M3x.-e-PX--`. |
| Has problems | Whether the check found a problem in the child. |

A score that could not be determined is an empty cell, never `0`. The `x` on an M-score is the
missing-information mark: information the scheme needs was missing, and the child could grade
better with it. A child with a problem is still
scored, with every cell that has a problem of kind missing, wrong type, out of range, not in
vocabulary or rule counted as empty, so fix the problems and check again to see the scores
the portal will give. A workbook with no children has the table with no rows, and the report says there is no child to score.

### The summary

The summary names the workbook file, the `ghfdb` version, which made the scores, the time of
the check in UTC, the releases of the vocabularies the check read, the number of children, the
number of problems, the number of children with problems and a link to the
[quality scheme](../reference/quality-scheme/index.md). When there is no problem it says so.

## Kinds of problem

| Kind | Meaning | Example |
|---|---|---|
| `missing` | A field that is mandatory in both domains, borehole and mine (`B`) and probe sensing (`S`), is empty. | Row 12 has no value in a mandatory field. |
| `wrong type` | A cell is not the field's type or does not match its pattern. A number stored as text is accepted. | `abc` in a number field. |
| `out of range` | A number is below the minimum or above the maximum, or text is longer than the maximum length. | A latitude of 120. |
| `not in vocabulary` | A value is not one of the field's allowed terms. | `granit` where `granite` is allowed, with `granite` as the suggestion. |
| `rule` | A cross-field rule is broken: the fields of one child do not say what the rule requires together. The problem is the field to fill in or to change, and the `Rule` and `Related` columns say which rule and why it applies. | An empty field that is mandatory for borehole and mine data only, in a child explored by drilling. |
| `unknown column` | A column of the workbook names no field. When its header is close to a published column name, that name is the suggestion. | A column headed `Notes`, or `Ref_ISGN` with `Ref_IGSN` as the suggestion. |
| `no column` | The workbook has no column for a field. A mandatory field is also `missing` on every child. | An upload template with a column deleted. |
| `duplicate column` | Two columns name the same field. The first is checked. | Two columns headed `P1`. |

A field that is mandatory in one domain only is not `missing` when it is empty. It is a `rule`
problem, and only for a child whose exploration method puts it in that domain.

A field that takes several values in a cell, written with a separator, is checked value by
value, and the problem names the value.

## How long a check takes

A workbook of 90,000 children, the size of the GHFDB, with every field filled, was checked and
checked, scored and reported in 11 seconds on the development machine, with the cross-field rules applied and one child in a hundred breaking a rule, once the vocabularies were cached. The test
suite fails the check when it takes 15 seconds.

## Python API

```{eval-rst}
.. automodule:: ghfdb.qc.report
   :members:

.. automodule:: ghfdb.cli
   :members:
```
