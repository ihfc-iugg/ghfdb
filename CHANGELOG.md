# Changelog

All notable changes to this project are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the package follows
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Scheme changes

- A child whose exploration method sends it to the probe-sensing or the borehole and mine
  rules, and whose every other field those rules read is empty, now has no T-score and no
  TC-score, and its M-score is `Mx`. The same holds for the scores of its own measurements. This
  is the sentence the corrigendum of Fuchs et al. (2023) adds to Section 3.2 (Fuchs et al.,
  2026, Tectonophysics 934, 231226): "If all metadata fields required for the scoring are
  missing, the M-score will appear as Mx."

### Changed

- The field reference pages no longer have a Source column in each field's table. The field
  schema still records the source of every fact.

## [v0.1.0] - 2026-11-10

### Added

- The `ghfdb` package, with an empty `ghfdb.qc` subpackage for quality control.
- `ghfdb.fields`, which describes the 74 fields of version 2026.03 of the submission template
  ([Fuchs et al., 2025](https://doi.org/10.5880/fidgeo.2025.042), `P1`-`P13`, `C1`-`C53` in the
  template's column order, and the assessment fields `A1`-`A8`): published column name, meaning, type,
  unit, range, obligation, domain, quality relevance and allowed values, each fact with its
  source. `load_schema()` reads them from a file shipped in the package with Frictionless
  and returns a `frictionless.Schema`. A field is looked up by its code with `get_field`, and by
  its published column name with `field_for_column()`. The facts Table Schema has no property for
  are in each field's `custom` dictionary.
- The allowed values of the 27 fields that take terms from a controlled vocabulary, read
  from the IHFC Controlled Vocabularies as currently published when the field definitions are
  loaded. The field schema links each of these fields to the permanent identifier of its
  concept scheme and, where it narrows the choice, its collection, and holds no term and no
  version. Each scheme's file is downloaded from its identifier the first time it is needed and
  downloaded again only when the server says it changed. The cache is in the user cache
  directory (`caching_session()` takes another). `frictionless`, `platformdirs`, `requests` and
  `requests-cache` are now runtime dependencies. The loaded schema is the complete Frictionless
  Table Schema, with the allowed values as `enum`, in memory.
- `ghfdb.fields.Vocabularies`, which downloads and reads the vocabulary files, and
  `allowed_values()`, which gives a field's values with the label and URI of each concept. The tests read
  the files as currently published, so they fail when the vocabularies change.
- `ghfdb.template.UploadTemplate`, which generates the upload template from the field schema
  (the three sheets, description rows and choice lists) and writes it to a path without
  replacing an existing file unless asked.
- The documentation site publishes the upload template generated for its version, with a
  list of how it differs from the hand-maintained template.
- Documentation: a developer guide for loading and looking up field definitions, and a Python
  API reference.
- The `ghfdb check <workbook>` command, which checks the `data list` sheet of a filled-in upload
  template against the field schema and the published vocabularies and writes
  `<name>.report.html` beside the workbook, a single web page with a summary and a table of
  problems. It
  gives status 0 for no problem, 1 for problems and 2 when it could not run. `ghfdb.qc.report.Report`
  writes the report, and `ghfdb.cli.main` and `ghfdb.cli.run` run the command.
- `ghfdb.Dataset`, the children of a workbook as one pandas table, with `Dataset.from_workbook`
  and `Dataset.check`. `fastexcel`, `pandas`, `pyarrow` and `jinja2` are now runtime
  dependencies.

- Cross-field rules, which relate several fields of one child. `ghfdb check` and
  `Dataset.check` apply them after the field check, and a child that breaks one gets a
  problem of the new kind `rule`. The report shows the rule's identifier linked to its entry
  in the published reference, its statement and the field that made it apply.
  `ghfdb.qc.rules` declares the rules.
- Four temperature fields from version 2026.03 of the submission template, after `C38`: `C50`
  (`T_top_mean`), `C51` (`T_top_uncertainty`), `C52` (`T_bot_mean`) and `C53`
  (`T_bot_uncertainty`), the absolute temperature at the top and bottom of the heat-flow interval
  used to calculate the temperature gradient, and its uncertainty.
- An `AllowedWhen` rule may have `alternatives`: further conditions, any one of which makes the
  rule apply. Rule CF-4 uses one.
- A field's `vocabulary` object may have `download` and `downloadFormat`, which name the file to
  download and its RDF format (`text/turtle` or `application/rdf+xml`) for a scheme that is not
  published as Turtle at its identifier, and a `termForm` of `localName`, which writes a term as
  the last segment of the concept's URI without square brackets. `Vocabularies.graph` takes the
  address and the format. The members of a collection that holds other collections are the
  members of all of them.

### Changed

- The problem table has two new columns, `rule` and `related`, after `suggestion`. They are
  set for a `rule` problem only. `Dataset.check` takes the rules to apply, which default to
  all of them.
- `Dataset.check` now reads the published vocabularies, from the user cache or by download,
  to resolve the concepts the rules name. Offline with an empty cache it raises `OSError`.
  A caller who loaded the schema with their own `Vocabularies` should pass the same one as
  `vocabularies`.
- openpyxl is now a runtime dependency, because `ghfdb.template` writes the upload template.
- The documentation build now checks that every concept, scheme and collection address in the
  field reference is an `http` or `https` address and encodes the brackets and parentheses that
  could end a Markdown link. An address that is anything else stops the build with a message
  naming it. The check uses the `validators` package, a new documentation dependency.
- The documentation loads mermaid 11.12.1 as a single script with a subresource integrity hash,
  so a browser refuses the file if the CDN serves anything other than the published build. It
  was loaded without one before. The diagrams are drawn as before. `docs/conf.py` holds the
  version and hash, with the command that produces a new hash for an upgrade.

- The reference template is version 2026.03 of the submission template. The documentation lists
  how the generated upload template differs from it, and reads its `controlled vocabulary` sheet
  by column letter.
- The fields are in the order of the template's columns, so `C50` to `C53` come between `C38`
  and `C39`.
- `C13` is titled "Flag sedimentation effect (heat flow correction)", `C24` "Surface/Bottom-water
  temperature" and `C29` "Corrected temperature gradient". The published column name of `C24` is
  `Surface_temperature`, and `water_temperature` is its earlier column name.
- The cross-field rules name the concepts by the hyphenated identifiers the vocabularies now
  publish (`drilling-clustering`, `probing-onshore`, `probing-offshore`, `probing-clustering`,
  `assumed-from-literature`, `core-samples`). With the underscored identifiers `ghfdb check`
  stopped with status 2.
- An unknown column carries as its suggestion the published column name it is closest to.
- A vocabulary file whose server sends no `ETag`, `Last-Modified` or `Cache-Control` is kept and
  used for a day, and downloaded again after that. Such a file was not kept at all before.
- Lithology and stratigraphic age take their terms from the CGI simple lithology vocabulary and
  the 2020 International Chronostratigraphic Chart, and still take several values separated by
  `;`. Article XI of the constitution allows them
  ([ADR 0007](docs/adr/0007-lithology-and-age-take-terms-from-external-vocabularies.md)).

### Removed

- `tc_pT_fuction` and `Ref_ISGN`, the misspelled column names that version 2026.03 of the
  template still prints, are no longer accepted as earlier names of `C46` and `C49`.
- The free-text guidance and the length limit of the lithology and stratigraphic age fields.

### Scheme changes

- Wrote down how several values in one field are read: number fields value by value with
  `C1` and `C2` paired, routing, flags and the two probe waivers reading the first filled value,
  and a borehole gradient's case chosen once for the child. The code already read them this way.
- Added rule CF-1: a child explored by drilling, clustered drilling, mining, tunneling or
  indirect estimation has every field mandatory for borehole and mine data only filled
  (`C4`, `C5`, `C31`, `C32`).
- Added rule CF-2: a child explored by probing, onshore, offshore or clustered, has every field
  mandatory for probe sensing only filled (`C6`, `C23`).
- Added rule CF-3: a thermal conductivity location of literature or unspecified (`C42`) is
  allowed only when the thermal conductivity source (`C41`) is assumed from literature.
- Added rule CF-4: a child whose temperature method at the top or at the bottom (`C31` or
  `C32`) is the enhanced geothermal response test has the thermal conductivity method (`C43`)
  probe - pulse technique. The source is section 6.1 of the description of version 2026.03 of
  the submission template.
- A workbook whose header carries `tc_pT_fuction` or `Ref_ISGN` has an unknown column, with
  `tc_pT_function` or `Ref_IGSN` as the suggestion, and the field has no column.
- The values `C25` (lithology) and `C26` (stratigraphic age) accept are now the 265 concepts of
  the CGI simple lithology vocabulary and the 178 geochronologic eras of the 2020 chart, written
  as the local name of the concept without brackets. Superseded names such as `CambrianStage5`
  are not accepted.
- Obligation and domain follow version 2026.03: `C46` is mandatory, `C4`, `C29` and `C30` are
  for borehole and mine data only, `P13` and `C24` are for both domains, so `C4` is now also
  required by CF-1. `C9` no longer accepts `[unspecified]`, `C38` accepts `[unspecified]` where
  it accepted `[Unspecified]`, and `A6` and `A7` take the continents and domains the template
  lists.
- `C24` keeps the range −9.99 to 999.99 and `C50` to `C53` take −99,999.99 to 99,999.99, the
  values of row 8 of the `data list` sheet where the template's two sheets differ.
- A field mandatory in one domain only is no longer left unchecked: when it is empty for a
  child of that domain, it is reported as a `rule` problem.
- The quality scheme is written down as a complete specification, the reference for how a child
  is scored. It starts from the scheme the GHFDB portal applies today, which follows version 0.2
  of the Heat Flow Quality Analysis Toolbox. The documentation has a page for each part: the
  U-score, the T-score and TC-score under the probe-sensing rules and under the borehole and
  mine rules, the M-score with its missing-information mark, the perturbation flags and the
  inherited code of a parent, each with a diagram of its decisions. Every rule names its source
  in Fuchs et al. (2023) or in the portal decision that changed it, and a page lists every
  departure from the paper with its reasoning. Six places where the paper is ambiguous or
  contradicts itself, or where the portal's description and code disagree, are put to the data
  assessment team as questions.
- The worked examples are published with the scheme in `ghfdb/qc/worked_examples.json`, 205
  examples giving each one's inputs by field code and its expected scores, every one asserted by
  the GHFDB portal's own tests. The documentation renders them as tables from that file.
- Preview quality scores. `ghfdb check` now scores every child under the quality scheme and the
  report gains a Preview scores table after the problems: the rules that scored the child,
  its U-score, T-score, TC-score and M-score, its perturbation flags and quality code, and
  whether the child has problems. Each score heading links to its page of the scheme
  reference, and the summary links to the scheme. A cell that has a problem is scored as
  empty. `Dataset.scores` gives the same table in Python. A workbook of 90,000 children is
  still checked, scored and reported in under 15 seconds.
