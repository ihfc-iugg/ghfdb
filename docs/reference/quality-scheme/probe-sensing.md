# Probe-sensing rules

The probe-sensing rules score a child whose exploration method is one of the probing methods:
`[Probing (onshore, lake, river, etc.)]`, `[Probing (offshore, ocean)]` and
`[Probing (clustered)]`. They give a T-score for the temperature gradient and a TC-score for
the thermal conductivity. Both start at 1.0 and each criterion adds a penalty, as
[the overview](index.md) describes, including what an empty and an unspecified input do.

Source for the whole page: Fuchs et al. (2023), with its corrigendum (Fuchs et al., 2026,
Tectonophysics 934, 231226, <https://doi.org/10.1016/j.tecto.2026.231226>), Section 3.2.1 and
Table 2. Later sources cite the corrigendum's table as "corrected Table 2".

## T-score

The T-score has four criteria: the probe penetration, the number of temperature recordings,
the water depth and the probe tilt. Its lowest value is {{ lowest('probe-t') }} and its highest
{{ highest('probe-t') }}.

### Fields read

{{ fields("P12", "P6", "C6", "C37", "C23", "C12", "C17") }}

```{mermaid}
flowchart TD
    gradient["Probe gradient"] --> penetration["Penetration"]
    gradient --> recordings["Number of recordings"]
    gradient --> corrected_water{"Bottom-water correction present and corrected?"}
    corrected_water -->|"Yes"| water_waived["Water depth: no penalty"]
    corrected_water -->|"No"| water["Water depth"]
    gradient --> corrected_tilt{"Temperature correction tilt corrected?"}
    corrected_tilt -->|"Yes"| tilt_waived["Tilt: no penalty"]
    corrected_tilt -->|"No"| tilt["Tilt"]
    penetration --> sum["T-score = the start value plus the penalties"]
    recordings --> sum
    water --> sum
    water_waived --> sum
    tilt --> sum
    tilt_waived --> sum
```

### Penetration

Reads `C6` `probe_penetration`, in metres.

{{ criterion('probe-t.penetration') }}

The field takes a number only, so it has no unspecified value. Source: corrected Table 2,
"Probe penetration". The table's ranges give each edge to one row.

### Number of temperature recordings

Reads `C37` `T_number`.

{{ criterion('probe-t.recordings') }}

Source: corrected Table 2, "Number of temperature points".

### Water depth

Reads `P6` `elevation`, in metres. The water depth is the elevation with its sign reversed.

{{ criterion('probe-t.water-depth') }}

An elevation of zero or above has no water depth, so the criterion is treated as empty: see
{ref}`DEP-7 <dep-7>`.

**Waived.** When `C17` `corr_SUR_flag` is `[Present and corrected]`, the criterion takes no
penalty and no mark, even when the elevation is empty.

Source: corrected Table 2, "Water depth", where the waiver is the bottom-water temperature flag
`{corr_BWT_flag}`. The template has no field of that name, and the scheme reads `C17`: see
{ref}`DEP-8 <dep-8>`.

### Tilt

Reads `C23` `probe_tilt`, in degrees.

{{ criterion('probe-t.tilt') }}

The range of `C23` does not allow a negative tilt.

**Waived.** When `C12` `corr_T_flag` is `[Tilt corrected]`, the criterion takes no penalty and
no mark, even when the tilt is empty. The corrected table conditions the waiver on the in-situ
correction `{corr_IS_flag}`, and the scheme reads the temperature correction `C12`, whose
vocabulary holds `[Tilt corrected]`: see {ref}`DEP-8 <dep-8>` and {{ decision(11) }}.

Source: corrected Table 2, "Tilt".

## TC-score

The TC-score has four criteria: the location, the saturation, the number of conductivity
measurements and the pT conditions. Its lowest value is {{ lowest('probe-tc') }} and its highest
{{ highest('probe-tc') }}. It reads nothing from the child, so the child's own score and its
TC-score are the same.

### Fields read

{{ fields("P12", "C42", "C41", "C43", "C44", "C47", "C45") }}

```{mermaid}
flowchart TD
    conductivity["Probe conductivity"] --> location["Location"]
    conductivity --> saturation["Saturation, method, source and location together"]
    conductivity --> literature{"Location literature?"}
    literature -->|"Yes"| skip["Number is not scored"]
    literature -->|"No"| number["Number of measurements"]
    conductivity --> pt["pT conditions and method"]
    location --> sum["TC-score = the start value plus the penalties"]
    saturation --> sum
    skip --> sum
    number --> sum
    pt --> sum
```

### Location

Reads `C42` `tc_location`.

{{ criterion('probe-tc.location') }}

Source: corrected Table 2, "Localization".

### Saturation

Reads `C44` `tc_saturation`, with `C43` `tc_method`, `C41` `tc_source` and `C42` `tc_location`.
The criterion is a list of rows. Every row whose conditions all hold counts, and the poorest
penalty wins.

{{ criterion('probe-tc.saturation') }}

A laboratory method is one of the six `[Lab …]` methods. A row that asks for every value to be
one holds only when every value of `C43` is a laboratory method, because the corrected table
adds the condition "`{tc_method}` is all with `[Lab - ...]`" to the onshore laboratory rows. A
child that lists a laboratory method beside another method is scored by the rows of the other
method, and the laboratory method fits no row.

* **Empty.** A row holds whatever the fields it does not name contain, so an empty field
  matters only when no row holds without it. A laboratory conductivity with `C41` empty is
  scored by the laboratory rows, which do not name `C41`. When no row holds and a field some row
  names is empty, the criterion takes the empty outcome of the table. Every row names `C43`, so
  an empty `C43` always takes it.
* **Unspecified.** An unspecified saturation, source or location is a value. It takes part in
  the rows above and, where it satisfies none, takes the unmatched outcome, without the mark.
* **No row holds.** A conductivity measured by `[Probe - continuous heating technique]` fits no
  row. It is under discussion (<https://github.com/ihfc-iugg/ghfdb/issues/42>). The vocabulary
  of `C43` has no `[Other]`, so the corrected table's row for it among the estimates has no
  term to score.
* **The offshore on-board rows.** The corrected table writes the method and source conditions
  once, against the first of its two offshore on-board rows. The scheme applies them to both.

Source: corrected Table 2, "Source type and saturation".

### Number of conductivity measurements

Reads `C47` `tc_number`, and `C42` for the exception.

{{ criterion('probe-tc.number') }}

Source: corrected Table 2, "Number of conductivities", with the condition that the location is
not literature or unspecified.

### Pressure and temperature conditions

Reads `C45` `tc_pT_conditions`, with `C43` `tc_method`. The criterion is a list of rows, scored
like the saturation.

{{ criterion('probe-tc.pT') }}

* **Empty.** A row holds whatever the fields it does not name contain. Only the first row names
  `C43`, so an empty `C43` matters only for actual in-situ conditions, and replicated, corrected
  and ambient conditions score by their own rows. When no row holds and a field some row names
  is empty, which is an empty `C45`, or an empty `C43` with actual in-situ conditions, the
  criterion takes the empty outcome of the table.
* **Unspecified.** `[Unspecified]` is a value, and takes the penalty of its row without the
  mark.
* **No row holds.** Actual in-situ conditions with a method other than the pulse probe hold no
  row, and take the unmatched outcome.

Source: corrected Table 2, "pT conditions".

## Worked examples

The [worked examples](worked-examples.md) give a gradient for every criterion of the T-score,
including both waivers, and a conductivity for every criterion of the TC-score, including the
literature exception, the empty inputs, an unspecified saturation and several conductivity
methods. Whole children scored by these rules are the examples named `P1` to `P5`.

## Under discussion

* <https://github.com/ihfc-iugg/ghfdb/issues/42>: how a conductivity measured with the continuous heating probe scores.
