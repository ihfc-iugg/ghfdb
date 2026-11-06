# Worked examples

The worked examples are children, measurements and parents with their inputs and the scores the
scheme gives them. They are the tests that every implementation of the scheme runs, and the
tables below are built from one file, so this page cannot disagree with it. The file is
[`ghfdb/qc/worked_examples.json`](https://github.com/ihfc-iugg/ghfdb/blob/main/ghfdb/qc/worked_examples.json)
in the package, and it is the single source of every example.

Every example is one that the GHFDB portal's own test suite asserts, with the same inputs and the
same expected scores, so the scheme and the portal agree by construction. The last column names
the portal tests behind each example and links the file that holds them.

## How to read the tables

* **Inputs** are given by field code. A field that is not listed is empty. A field with several
  values lists them separated by commas. The legend below names each field code.
* **Expected** gives only the values the portal's test asserts. A T-score or TC-score that reads
  *not determined* is empty, and is never 0.
* **no mark** and **missing-information mark** say whether the score or the M-score carries the
  mark. The M-score of a child carries it as an `x`.
* **own scores** are the T-score and the TC-score of the child's gradient and conductivity
  before the child's own corrections are applied. They are given for a child only where they are
  asserted. See [the overview](index.md).
* **own T-score** and **own TC-score** mark an example that scores a gradient or a conductivity
  on its own, without a child. Its score then applies none of the child's correction rules,
  unless a correction field is listed among its inputs.

## The fields the examples use

{{ field_legend() }}

## Which rules score a child

{{ examples("routing") }}

## U-score

{{ examples("u-score") }}

## Probe sensing: T-score

{{ examples("probe-t") }}

## Probe sensing: TC-score

{{ examples("probe-tc") }}

## Borehole and mine: T-score

{{ examples("borehole-t") }}

## Borehole and mine: TC-score

{{ examples("borehole-tc") }}

## M-score

The inputs are the child's T-score and TC-score, and whether each carries the mark.

{{ examples("m-score") }}

## Perturbation flags

{{ examples("perturbation-flags") }}

## Inherited code

The inputs are the quality codes of the children a parent could rest on, in order, and `C9`
where a child's relevance matters.

{{ examples("inheritance") }}

## Whole children

{{ examples("child") }}

## What the examples cover

Every criterion of every part of the scheme has at least one example. Each row names a
criterion, and lists how many examples exercise it and the first three.

{{ coverage() }}
