# ADR 0010 — Each scheme criterion is declared once

**Status:** accepted. It extends [ADR 0006](0006-cross-field-rules-are-declared-in-python.md) from
the cross-field rules to the scoring.

## Context

The first implementation of the quality scheme scored every child correctly and was hard to
change. An audit of it found three problems that this decision answers:

1. A criterion's knowledge was split across files and written in several styles. The concept
   classes of a borehole criterion were in one module and their penalties in another. The
   penalties and thresholds of a probe criterion were written inline in method bodies. The
   documentation then restated every number twice, in a table and in a diagram, and nothing
   failed when one of the three was forgotten.
2. The same operation, giving each value the penalty of its class, was coded five different ways,
   so two criteria that scored alike did it by different routes.
3. The list of concepts that guards the scheme against a vocabulary change was kept by hand. A
   class left out of the list never failed. The term simply never matched.

## Decision

Each criterion of the scheme is one declaration, a `Criterion` in `ghfdb.qc.penalties`. It carries
the identifier the worked examples use, a title, the paper's table and row it comes from, and one
table that gives the penalties. There are three kinds of table, and the scoring uses nothing else
to turn a value into a penalty:

* `Bands`: a number against ordered edges.
* `Classes`: a term against groups of concepts.
* `Cases`: rows of conditions on several fields, the poorest row that holds counting.

Each table scores every child at once, keeps the poorest of a child's values, takes its largest
penalty from its own rows, and lists the concepts it names. A table may read its number through a
declared conversion, as the water depth reads the elevation with its sign reversed. The criteria
are declared as module-level constants in `ghfdb.qc.probe` and `ghfdb.qc.borehole`. Each set of
rules is a `RuleSet` in `ghfdb.qc.ruleset` that lists the criteria its scores add up, the
corrections that waive one, and the criterion that stands in for another in a measurement's own
score, and `ghfdb.qc.criteria` lists every declared criterion from them. What a table cannot say
stays code: which of the three cases a borehole gradient is, and the interval depth gate.

The scheme pages render each criterion's penalty table from its declaration, through the
`criterion()` function of the documentation extension. A diagram keeps the structure of the
scoring and carries no number. The concepts that the scoring resolves to vocabulary terms, and
refuses when the vocabulary no longer holds one, are read from the declarations.

Python source names a field by its published column name, through the generated `Field`, and the
data stays keyed by field code. A dataset therefore keeps one column per field code
([ADR 0005](0005-a-dataset-holds-one-pandas-dataframe.md)), and a correction of a column name
changes one line of the generated names and no worked example.

## Consequences

* A change of a penalty, an edge or a group is one edit to a declaration, and a new criterion is
  scored once it is listed in its set of rules. The page that states it
  and the tests that run it follow, and a criterion that a worked example does not reach is
  found, because every declared criterion has an example.
* A scheme change that adds a kind of condition adds it to the table that needs it. The probe
  saturation's laboratory rows hold only when every value of the conductivity method is a
  laboratory method, which `Cases` states as a row that needs every value of a field.
* The concept lists cannot drift from what the scoring reads, because the lists are read from the
  declarations.
* A criterion that is not a table of one of the three kinds, such as the coefficient classes of
  the U-score and the product classes of the M-score, is not declared this way, and its page
  table stays hand-written.

## Revisit if

A criterion of the scheme needs a fourth kind of table, or another implementation of the scheme
needs to read the declarations. In the second case a machine-readable copy can be generated from
the criteria, as ADR 0006 says for the rules.
