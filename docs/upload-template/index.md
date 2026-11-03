# Upload template

This guide is for a data assessor or contributor who fills in the GHFDB upload template with
heat-flow data. Download the template for this version of ghfdb, enter your data on its
`data list` sheet and follow the choice lists where a field offers them.

{upload-template-download}

## The three sheets

The workbook has three sheets:

- `readme` names the package version and the vocabulary release the template was generated
  from, and links the field reference.
- `data list` is the sheet you fill in. Row 1 holds the field codes. Rows 2 to 8 describe
  each field: its obligation, domain, quality relevance, name, published column name, unit and
  allowed range of values. Enter one record per row from row 9.
- `controlled vocabulary` lists the allowed terms of each field that has a fixed list.

Every field is described in full in the [field reference](../reference/fields/index.md).

## Fill in the template

1. Download the workbook above and open it in a spreadsheet program.
2. Go to the `data list` sheet and read rows 2 to 8 of the column you are filling in.
3. Enter your values from row 9. Where a cell offers a choice list, pick a term from it.
4. Save the workbook under a name of your own.

## Changes from the hand-maintained template

This template replaces the one the GHFDB portal has distributed until now. The lists below are
computed from the two workbooks each time the documentation is built, so they show every
difference.

{upload-template-changes}

## Why the template is generated

The template is generated from the field reference, so the two cannot disagree. A field
schema and a vocabulary release go into the package's upload template generator, and the
documentation build writes the result beside this page.

```{mermaid}
flowchart LR
    schema["Field schema"] --> template["Upload template generator"]
    release["Vocabulary release"] --> template
    template --> build["Documentation build"]
    build --> download["Download on this page"]
```

## Why choice lists accept any value

Fields with a fixed list of allowed values get a choice list. The list offers the allowed
terms and accepts any value, so a term that is not offered can still be entered. The readme
sheet names the package version and the vocabulary release, so a workbook can always be traced
to the template it came from.
