# ghfdb Constitution

The rules every change to this repository follows. The words in it are defined in
[`CONTEXT.md`](CONTEXT.md).

## Core articles

### Article I — Testing
Every change follows [`docs/contributing/standards/testing.md`](docs/contributing/standards/testing.md): what gets a test
and what does not, the test-first cycle, test structure and the coverage floor.

### Article II — Simplicity
Simplicity means less custom code and more reliance on established, maintained packages. Where
such a package does the job, use it, and use its own types: do not write a wrapper around it, a
copy of its types or a hand-built version of what it does. A package's size, and the packages it
brings in, are never a reason against it. Where no package does the job, start with the simplest
design that does. A new abstraction or piece of infrastructure needs a stated reason in the pull
request.

### Article III — Anti-Abstraction
No wrapper layers, base classes or indirection without a present, concrete second use. Prefer
duplication over the wrong abstraction.

### Article IV — Integration-First
The package is used through its command line and through the workbooks it reads and writes.
Behaviour is tested the way an assessor meets it: a workbook in, a report out.

### Article V — Security & data-safety
Secrets live in runtime configuration, never in the repository. A workbook is untrusted input.
Its formulas are never evaluated, and its contents are never executed or used to build a path
or a command.

### Article VI — Documentation
A change to what a user sees, runs or reads in a report updates the README, the documentation and
`CHANGELOG.md` in the same pull request. Docstrings and comments follow
[`docs/contributing/standards/code-documentation.md`](docs/contributing/standards/code-documentation.md), and pages under
`docs/` follow [`docs/contributing/standards/documentation.md`](docs/contributing/standards/documentation.md). The
documentation builds with warnings treated as errors.

### Article VII — Dependency discipline
Prefer an established, maintained package to custom code. A package is turned down only if it is
unmaintained, is not established, or does not do the job. Its size and its own dependencies are not
reasons. The pull request that adds a package says which custom code it replaces, or why no package
does the job. `deptry` passes: no unused, missing or transitively relied-upon dependencies, so every
package the code imports is declared in the group that uses it.

### Article VIII — Cohesion
Related behaviour is grouped in a class, not scattered across module-level functions. Two or more
module-level functions share a subject when they operate on the same data, take the same first
argument, are only meaningful in sequence, or are named around the same noun. A module-level
convenience function is only a thin wrapper over the class. A genuinely standalone pure function,
a pytest fixture and a command-line entry point are exempt. Article III still holds: grouping
today's behaviour is the goal, not a base class or a hierarchy built for a second implementation
that does not exist.

## Project articles

### Article IX — Every rule names its source
Every check and every scoring rule names where it comes from: a section or table of Fuchs et al.
(2023), or the recorded decision that changed it. A rule with no source is a defect.

### Article X — Rules, examples and code change together
A change to a validation rule or to the quality scheme changes, in one pull request, the
documentation that states the rule, the worked examples that test it, and the code. The pull
request records the change in `CHANGELOG.md` under a **Scheme changes** heading.

### Article XI — The vocabulary comes from the published vocabularies
No vocabulary term is typed into the code or the field schema by hand. Allowed values come from
the IHFC Controlled Vocabularies as published at their permanent identifiers, which the field
schema links to.

### Article XII — Report, never modify
No code path writes to a workbook it was given to check. Every problem is reported as what it is:
an invalid value is never reported as missing, a value is never coerced or truncated without a
problem being reported, and a row number is the row number in Excel.

### Article XIII — Whole columns, not rows
Checks and scores operate on whole columns. A loop over rows in Python, including `iterrows`,
`itertuples` and a row-wise `apply`, needs a stated reason in the pull request.

### Article XIV — Compatibility
The public interface is the command line, the report layout and the `ghfdb` Python API. It
follows Semantic Versioning. Before 1.0.0, a breaking change is allowed in a minor release and
is recorded in `CHANGELOG.md`.

### Article XV — Stack
Python 3.12 or later, managed with uv and built with hatchling. pandas for tabular data. pytest
runs the tests, pre-commit runs the linters, mypy checks types, and Sphinx with MyST builds the documentation. CI
is this repository's own workflows.

## Articles not adopted

- Internationalization — the package has no translatable interface. Its command-line output and
  reports are in English.
- Data-model conventions (Django) — the package does not use Django and has no models.

## Quality bar

Read at plan and review; applies to every change.

- Test coverage meets the floor in `docs/contributing/standards/testing.md`.
- Every worked example passes with its exact expected scores.
- pre-commit, `mypy`, `deptry` and the documentation build pass.
- The package builds, its metadata is valid, and the README renders on PyPI (absolute URLs).
- Every change to the public interface updates the README, the documentation and
  `CHANGELOG.md`.

## Non-negotiables

- Tests, build and lint pass before a change merges. Nobody overrides a red check.
- The default branch requires one approval, and the author of a change never approves it.

---

**Version**: 1.1.0 | **Ratified**: 2026-11-03 | **Last Amended**: 2026-11-04
