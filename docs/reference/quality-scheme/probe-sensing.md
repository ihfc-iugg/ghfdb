# Probe-sensing rules

The probe-sensing rules score a child whose exploration method is one of the probing methods:
`[Probing (onshore, lake, river, etc.)]`, `[Probing (offshore, ocean)]` and
`[Probing (clustered)]`. They give a T-score for the temperature gradient and a TC-score for
the thermal conductivity. Both start at 1.0 and each criterion adds a penalty, as
[the overview](index.md) describes, including what an empty and an unspecified input do.

Source for the whole page: Fuchs et al. (2023), Section 3.2.1 and Table 2.

## T-score

The T-score has four criteria: the probe penetration, the number of temperature recordings,
the water depth and the probe tilt. Its lowest value is 0.2 and its highest 1.2.

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

The field takes a number only, so it has no unspecified value. Source: Fuchs et al. (2023),
Table 2, "Probe penetration". The paper's ranges share their end points, and the scheme uses the
toolbox's edges: {{ decision(1) }}. See {ref}`DEP-7 <dep-7>`.

### Number of temperature recordings

Reads `C37` `T_number`.

{{ criterion('probe-t.recordings') }}

Source: Fuchs et al. (2023), Table 2, "Number of temperature points". Bin edges:
{{ decision(1) }}.

### Water depth

Reads `P6` `elevation`, in metres. The water depth is the elevation with its sign reversed.

{{ criterion('probe-t.water-depth') }}

An elevation of zero or above has no water depth, so the criterion is treated as empty.

**Waived.** When `C17` `corr_SUR_flag` is `[Present and corrected]`, the criterion takes no
penalty and no mark, even when the elevation is empty.

Source: Fuchs et al. (2023), Table 2, "Water depth", where the correction is the bottom-water
temperature flag. The treatment of an elevation at or above sea level is {{ decision(1) }}. See
{ref}`DEP-7 <dep-7>`.

### Tilt

Reads `C23` `probe_tilt`, in degrees.

{{ criterion('probe-t.tilt') }}

A tilt below 0° fits none of the classes and takes −0.2 without the mark. The range of `C23`
does not allow a negative tilt.

**Waived.** When `C12` `corr_T_flag` is `[Tilt corrected]`, the criterion takes no penalty and
no mark, even when the tilt is empty. The paper conditions the tilt rule on the in-situ
correction `C11`, and the scheme reads the temperature correction `C12`, whose vocabulary holds
`[Tilt corrected]`: {{ decision(11) }}. See {ref}`DEP-8 <dep-8>`.

Source: Fuchs et al. (2023), Table 2, "Tilt".

## TC-score

The TC-score has four criteria: the location, the saturation, the number of conductivity
measurements and the pT conditions. Its lowest value is 0.2 and its highest 1.2. It reads
nothing from the child, so the child's own score and its TC-score are the same.

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

Source: Fuchs et al. (2023), Table 2, "Localization".

### Saturation

Reads `C44` `tc_saturation`, with `C43` `tc_method`, `C41` `tc_source` and `C42` `tc_location`.
The criterion is a list of cases. Every case whose conditions all hold counts, and the poorest
penalty wins.

{{ criterion('probe-tc.saturation') }}

* **Empty.** When any of `C44`, `C43`, `C41` or `C42` is empty, the criterion takes −0.2 with the
  mark, because every case of the list names those four fields.
* **Unspecified.** An unspecified saturation, source or location is a value. It takes part in
  the cases above and, where it satisfies none, takes −0.2 without the mark.
* **No case holds.** The criterion takes −0.2 without the mark. A conductivity measured by
  `[Probe - continuous heating technique]` fits no case. It is under discussion (<https://github.com/ihfc-iugg/ghfdb/issues/42>).

Source: Fuchs et al. (2023), Table 2, "Source type and saturation". The paper's table is
narrower than the cases above, and the scheme follows the toolbox: {{ decision(1) }}. See
{ref}`DEP-9 <dep-9>`.

### Number of conductivity measurements

Reads `C47` `tc_number`, and `C42` for the exception.

{{ criterion('probe-tc.number') }}

Source: Fuchs et al. (2023), Table 2, "Number of conductivities", with the condition that the
location is not literature or unspecified.

### Pressure and temperature conditions

Reads `C45` `tc_pT_conditions`, with `C43` `tc_method`. The criterion is a list of cases, scored
like the saturation.

{{ criterion('probe-tc.pT') }}

* **Empty.** When `C45` or `C43` is empty, the criterion takes −0.2 with the mark.
* **Unspecified.** `[Unspecified]` is a value and takes −0.2 without the mark.
* **No case holds.** The criterion takes −0.2 without the mark. Actual in-situ conditions with
  a method other than the pulse probe hold no case.

Source: Fuchs et al. (2023), Table 2, "pT conditions".

## Worked examples

The [worked examples](worked-examples.md) give a gradient for every criterion of the T-score,
including both waivers, and a conductivity for every criterion of the TC-score, including the
literature exception, the empty inputs and an unspecified saturation. Whole children scored by
these rules are the examples named `P1` to `P5`.

## Under discussion

* <https://github.com/ihfc-iugg/ghfdb/issues/42>: how a conductivity measured with the continuous heating probe scores.
