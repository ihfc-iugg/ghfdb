# Field reference

The field reference describes every column of the GHFDB upload template: what the column
holds, its type, unit and range, whether it must be filled in, which kind of data it applies
to, how it counts towards the quality score and, for columns that take terms from a controlled
vocabulary, every term you may write. Each fact names the source it was taken from.

The pages are built from the same field definitions that the `ghfdb` package ships, so they
cannot disagree with it.

## Find a field

Look a field up by its field code, such as `C43`, or by its published column name, such as
`tc_method`. Both lead to the same entry. The table below lists all fields in field-code order;
select a code or a column name to open its entry.

The entries are grouped on three pages:

```{toctree}
:maxdepth: 1

parent
child
assessment
```

{field-index}

## Where the facts and allowed values come from

Every fact in an entry comes from one of four places, named in the Source column:

- **Upload template**: the current GHFDB upload template.
- **Fuchs et al. (2023), Appendix A**: the table of fields in the paper that describes the
  quality scheme.
- **A recorded decision**: where the two disagree, or neither says, a decision was recorded and
  is linked from the entry.
- **IHFC Controlled Vocabularies**: the allowed values of a field that takes terms from a
  controlled vocabulary come from one stated release of the vocabularies, named in the entry
  together with its DOI.

```{mermaid}
flowchart LR
    template[Upload template] --> facts[Facts about each field]
    appendix[Fuchs et al. 2023, Appendix A] --> facts
    decisions[Recorded decisions] --> facts
    release[Stated vocabulary release] --> values[Allowed values]
    facts --> reference[Field reference]
    values --> reference
```

## How a newer vocabulary release is adopted

The field schema names one release of the IHFC Controlled Vocabularies and, for each
vocabulary field, the concept scheme and the collection it takes its terms from. It holds no
term. The terms are read from the named release when the schema is loaded, so this reference
always shows exactly what that release publishes. When the vocabularies publish a new
release, a maintainer changes the release the schema names, and the tests show what depends
on the terms that moved. The steps are in
[Adopt a new vocabulary release](../../contributing/vocabulary-release.md).

```{mermaid}
flowchart LR
    named[Maintainer names the new release] --> downloaded[The release is downloaded]
    downloaded --> read[Allowed values are read from it]
    read --> pages[This reference shows the new terms]
```

## Download the schema

The facts on these pages are also available as a machine-readable file:
{download}`ghfdb-field-schema.json <ghfdb-field-schema.json>`. It is a Frictionless Table
Schema that lists the allowed values of each vocabulary field, as read from the release.
