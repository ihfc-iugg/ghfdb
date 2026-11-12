# ADR 0009 — Several values in a scored field come only from Python

**Status:** accepted

## Decision

A field the quality scheme scores holds several values only when a dataset built in Python holds a
list in its cell. Text in a scored field is never split. Each criterion that gives a penalty scores
every value and takes the poorest. Routing and the perturbation flags read the first value.

## Why

The scheme scores every value of a field that holds several and takes the poorest, and four of its
worked examples give one. The field schema gives none of the scored fields a separator, and the
scheme's overview says the upload template holds one value in each field it scores. Splitting text
by a separator the schema does not declare would score a workbook differently from how the check
reads it, so a workbook can never reach this rule. A list in a cell is how data held elsewhere,
such as the GHFDB portal's, is passed in.

## Revisit if

The field schema gives a scored field a separator, so that a workbook can hold several values in
it.
