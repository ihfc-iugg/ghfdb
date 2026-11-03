# Domain Docs

Which of this repository's domain documents to read before working in it, and in what order.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root — the glossary.
- **`CONSTITUTION.md`** — the rules every change follows.
- **`docs/adr/`** — architectural decisions, when there are any.
- **`docs/developer/brainstorm.md`** — working notes from before the package was written. Not decisions.

This is a single-context repo. There is no `CONTEXT-MAP.md`.

## File structure

```
/
├── src/ghfdb/              ← the package
│   └── qc/                 ← quality control for upload template workbooks
├── tests/                  ← the test suite
├── docs/                   ← the documentation site
├── CONTEXT.md              ← glossary
└── CONSTITUTION.md         ← rules and quality bar
```

## The rules are scientific

What a quality rule means is defined by Fuchs et al. (2023), *Quality-assurance of heat-flow data:
The new structure and evaluation scheme of the IHFC Global Heat Flow Database*, Tectonophysics
863, 229976, and by the decisions recorded since. The GHFDB portal's quality-score guide and
decision record are the most complete account of the scheme as currently applied. Never write or
change a rule from inference. Take it from those sources or from the maintainers in an issue.

## Use the glossary's vocabulary

When your output names a concept from this repository — in an issue title, a pull request or a
test name — use the term as defined in `CONTEXT.md`. If the term you need is not there, either
you are inventing language the project does not use, or there is a gap worth recording.
