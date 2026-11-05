# ADR 0005 — A dataset holds one pandas DataFrame, by composition

**Status:** accepted

## Decision

Tabular data is held in pandas. `ghfdb.Dataset` holds one public pandas DataFrame, `data`, with
one row per child and one column per field, named by field code. A dataset read from a workbook is
indexed by Excel row. `Dataset` is an ordinary class that holds the DataFrame. It is not a
`DataFrame` subclass and not a pandas accessor. The checks, and the scores and other operations
added later, are methods of `Dataset` or work on its `data`. Anything a dataset needs that pandas
does not provide, such as metadata, reading other sources, merging datasets or submitting to the
GHFDB portal, is added to `Dataset` when a feature needs it.

## Why

The checks were measured in pandas and in polars on 90,000 children: 0.6 s and 0.3 s, with the same
problems found. The speed of a check comes from reading the workbook in Rust and from working on
whole columns, not from the frame library. Quality scoring works on the same data, so a second
frame library would be loaded for nothing. The researchers who will use the package, and read and
propose its rules, work in pandas. The constitution's stack article already names it.

A subclass or an accessor attaches what it knows to one DataFrame object. That is lost when the
DataFrame is filtered, sorted or merged, which is most of what a researcher does with it, and
pandas' documentation steers away from subclassing for that reason. A class that holds the
DataFrame keeps the dataset's own facts and methods in one place and leaves the DataFrame plain,
so all of pandas works on it.

## Revisit if

A dataset needs more than one table, for example parents beside their children, which changes
what `Dataset` holds. Or pandas cannot meet a measured speed target that another frame library
can.
