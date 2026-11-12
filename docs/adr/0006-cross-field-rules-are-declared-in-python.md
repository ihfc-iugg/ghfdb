# ADR 0006 — Cross-field rules are declared in Python, each kind checking itself

**Status:** accepted. [ADR 0011](0011-concepts-are-referenced-through-the-vocabularies.md) replaces
how a rule names a concept, which the second paragraph of the decision records as it was decided;
the rest stands.

## Decision

The rules that relate several fields of a child are declared in Python, in `ghfdb.qc.rules`. Every
rule is an instance of a frozen dataclass derived from `Rule`, defined in
`ghfdb.qc.engine.rule_kinds`, which carries its identifier,
statement, source, reasoning and worked example. Each kind of rule is a subclass that implements
`problems()`, which finds the children breaking the rule a column at a time, and `diagram()`,
which draws the rule for the documentation. `RULES` is a tuple of every rule the check applies.
The check, the rule reference in the documentation and the tests all import it.

A rule names a vocabulary concept by its local name, the last segment of its URI, within the
vocabulary of the field the rule sets a condition on. The names are turned into terms from the
vocabularies as published, so no term is written in the code.

## Why

The field schema is a JSON file because it is a Frictionless Table Schema, a published format that
other tools read (ADR 0004). Cross-field rules have no such format, and nothing outside this
package reads them. Kept in Python, every rule is checked by the type checker and the linters. A
rule without a source or a worked example is refused before any test runs, and a misspelt concept
name is refused when the check is built, naming the rule, the field and the name. One set of objects drives the check, the documentation and the tests, so the
three cannot disagree, which the constitution requires of rules (Article X).

A method on each kind of rule, rather than a branch on the kind inside the check, means a rule that
fits no existing kind is added as a new subclass with its own `problems()` and `diagram()`. The
check itself does not change.

## Revisit if

Another implementation, such as the GHFDB portal, needs to read the rules. If so, a
machine-readable copy can be generated from `RULES`, as citable releases of the quality scheme may
need.
