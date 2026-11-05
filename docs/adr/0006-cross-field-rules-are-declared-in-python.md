# ADR 0006 — Cross-field rules are declared in Python, each kind checking itself

**Status:** accepted

## Decision

The rules that relate several fields of a child are declared in Python, in `ghfdb.qc.rules`. Every
rule is an instance of a frozen dataclass derived from `Rule`, which carries its identifier,
statement, source, reasoning and worked example. Each kind of rule is a subclass that implements
`problems()`, which finds the children breaking the rule a column at a time, and `diagram()`,
which draws the rule for the documentation. `RULES` is a tuple of every rule the check applies.
The check, the rule reference in the documentation and the tests all import it.

A rule names vocabulary concepts by their URIs, and they are turned into terms from the
vocabularies as published, so no term is written in the code.

## Why

The field schema is a JSON file because it is a Frictionless Table Schema, a published format that
other tools read (ADR 0004). Cross-field rules have no such format, and nothing outside this
package reads them. Kept in Python, every rule is checked by the type checker and the linters. A
rule without a source or a worked example is refused before any test runs, and a misspelt concept
name is a lint error. One set of objects drives the check, the documentation and the tests, so the
three cannot disagree, which the constitution requires of rules (Article X).

A method on each kind of rule, rather than a branch on the kind inside the check, means a rule that
fits no existing kind is added as a new subclass with its own `problems()` and `diagram()`. The
check itself does not change.

## Revisit if

Another implementation, such as the GHFDB portal, needs to read the rules. If so, a
machine-readable copy can be generated from `RULES`, as citable releases of the quality scheme may
need.
