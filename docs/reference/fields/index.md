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
  controlled vocabulary come from the vocabularies as currently published. The entry links to the
  permanent identifier of the concept scheme, and of the collection where there is one.

```{mermaid}
flowchart LR
    template[Upload template] --> facts[Facts about each field]
    appendix[Fuchs et al. 2023, Appendix A] --> facts
    decisions[Recorded decisions] --> facts
    vocabularies[Published vocabularies] --> values[Allowed values]
    facts --> reference[Field reference]
    values --> reference
```

## How the allowed values stay current

The field schema links each vocabulary field to the permanent identifier of its concept scheme
and, where it narrows the choice, of a collection. It holds no term. The terms are read from the
file published at the identifier when the schema is loaded, so this reference shows what the
vocabularies publish when the documentation is built. When the vocabularies change, the tests
show what depends on the terms that moved. See
[How the vocabularies are fetched](../../contributing/vocabularies.md).

```{mermaid}
flowchart LR
    identifier[Field links to a vocabulary identifier] --> downloaded[The published file is downloaded]
    downloaded --> read[Allowed values are read from it]
    read --> pages[This reference shows the terms]
```

## Download the schema

The facts on these pages are also available as a machine-readable file:
{download}`ghfdb-field-schema.json <ghfdb-field-schema.json>`. It is a Frictionless Table
Schema that lists the allowed values of each vocabulary field, as read from the published vocabularies.
