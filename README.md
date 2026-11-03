# ghfdb

[![PyPI version](https://img.shields.io/pypi/v/ghfdb.svg)](https://pypi.org/project/ghfdb/)
[![Development status](https://img.shields.io/pypi/status/ghfdb.svg)](https://pypi.org/project/ghfdb/)
[![Python versions](https://img.shields.io/pypi/pyversions/ghfdb.svg)](https://pypi.org/project/ghfdb/)
[![Checks](https://github.com/ihfc-iugg/ghfdb/actions/workflows/checks.yml/badge.svg)](https://github.com/ihfc-iugg/ghfdb/actions/workflows/checks.yml)
[![Coverage](https://codecov.io/gh/ihfc-iugg/ghfdb/graph/badge.svg)](https://codecov.io/gh/ihfc-iugg/ghfdb)
[![Documentation](https://github.com/ihfc-iugg/ghfdb/actions/workflows/pages.yml/badge.svg)](https://ihfc-iugg.github.io/ghfdb/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/ihfc-iugg/ghfdb/blob/main/LICENSE)

Python tools for working with the Global Heat Flow Database (GHFDB), the International
Heat Flow Commission's compilation of terrestrial and marine heat-flow measurements.

The first part, `ghfdb.qc`, is quality control for GHFDB data template workbooks. It
checks a workbook against the field schema and the
[IHFC Controlled Vocabularies](https://github.com/ihfc-iugg/controlled-vocabularies),
and scores each heat-flow determination with the GHFDB quality scheme: the uncertainty
score, the methodological score and the perturbation flags of Fuchs et al. (2023),
[doi:10.1016/j.tecto.2023.229976](https://doi.org/10.1016/j.tecto.2023.229976).

The package is in early development and does not yet check or score anything.

## Field definitions

`ghfdb.fields` holds what the upload template records about each of its 70 fields: the
published column name, meaning, type, unit, range, obligation, domain and quality relevance,
and the allowed values of every field that takes terms from a controlled vocabulary, each
fact with its source. It needs no network access.

```python
from ghfdb.fields import FieldSchema

schema = FieldSchema.load()
print(schema["tc_method"].allowed_values[0].term)  # or schema["C43"]
```

See the [developer guide](https://ihfc-iugg.github.io/ghfdb/developer/field-definitions.html).

## Why

Data assessors prepare heat-flow datasets in the GHFDB data template before they are
submitted. They need to know, before submission, whether every field is filled in
correctly, uses the agreed vocabulary, and what quality scores the data will receive.
The tool used for this so far has drifted from both the published vocabularies and the
quality scheme. This package replaces it with checks that read the published
vocabularies directly and scoring rules that are documented, versioned and tested
against agreed worked examples.

## Scope & philosophy

**What it is**

- An offline tool for data assessors working on their own workbooks.
- The reference for the GHFDB validation rules and quality scheme, developed in the
  open in this repository's issues.
- The source of the GHFDB upload template, generated from a machine-readable field
  schema.

**What it deliberately is not**

- Not the GHFDB portal's validation or scoring. The portal calculates its own scores
  and its values are authoritative. Scores computed here are a preview.
- Not a data editor. It reports problems and never changes a workbook.
- Not a store or an importer. Data goes to the GHFDB through the portal.

**Tie-break principles**

- The published IHFC vocabularies are the only source of allowed terms.
- Every rule is documented, versioned and covered by a worked example. A rule that is
  not written down is a defect.
- A problem is reported exactly as it is: an invalid value is never reported as a
  missing one, and nothing is corrected silently.
- A preview score that disagrees with the GHFDB portal is a defect. It is investigated
  and fixed in whichever codebase is wrong.
- The documentation is written for someone who does not read code. Every process is
  also shown as a simple diagram.

## Contributing

Proposals for a new check, a change to a rule or a change to the quality scheme start as an
[issue](https://github.com/ihfc-iugg/ghfdb/issues), where they are discussed and agreed before a
pull request is opened.

## Licence

The code is released under the [MIT Licence](https://github.com/ihfc-iugg/ghfdb/blob/main/LICENSE).
