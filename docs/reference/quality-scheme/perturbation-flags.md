# Perturbation flags

The perturbation flags record which disturbing effects the authors of a heat-flow value
recognised, and whether they corrected for them. They are seven characters, one for each effect,
and they are the last part of the quality code: in `U2.M3x.-e-PX--` they are `-e-PX--`. The flags
never change the U-score or the M-score.

## Fields read

One field of the child holds the state of each effect. The order of the characters is the order
of the table.

| Position | Flag | Effect | Field code | Published column name |
|---|---|---|---|---|
| 1 | `S` | Sedimentation | {ref}`C13 <field-c13>` | `corr_S_flag` |
| 2 | `E` | Erosion | {ref}`C14 <field-c14>` | `corr_E_flag` |
| 3 | `T` | Topography and bathymetry | {ref}`C15 <field-c15>` | `corr_TOPO_flag` |
| 4 | `P` | Paleoclimate | {ref}`C16 <field-c16>` | `corr_PAL_flag` |
| 5 | `V` | Surface and bottom-water temperature variation | {ref}`C17 <field-c17>` | `corr_SUR_flag` |
| 6 | `C` | Convection | {ref}`C18 <field-c18>` | `corr_CONV_flag` |
| 7 | `R` | Heat refraction | {ref}`C19 <field-c19>` | `corr_HR_flag` |

Source: Fuchs et al. (2023), Section 3.3 and Fig. 4. The paper's Table 5 writes heat refraction
as `h/H` and swaps the fifth and sixth characters. Its text, its Fig. 4 and the toolbox write
heat refraction as `R`, with surface-temperature variation fifth and convection sixth, and the
scheme follows them: {{ decision(6) }}. See {ref}`DEP-2 <dep-2>`.

The in-situ correction {ref}`C11 <field-c11>` and the temperature correction
{ref}`C12 <field-c12>` write no flag. They enter the T-score and the TC-score instead.

## How each flag is written

Each correction field takes one of five values.

| Value of the field | Character | Meaning |
|---|---|---|
| `[Present and corrected]` | the upper-case letter | The effect is present and was corrected |
| `[Present and not corrected]` | the lower-case letter | The effect is present and was not corrected |
| `[Present and not significant]` | `X` | The effect is present and assumed to be insignificant |
| `[Not recognized]` | `x` | The effect was not recognised, or is assumed not to be present |
| `[Unspecified]`, or empty | `-` | No information is held |

An empty field and an unspecified field are written the same way, as `-`. Source: Fuchs et al.
(2023), Section 3.3, where a minus sign stands for data with insufficient information, "empty or
unspecified". The two differ only for the in-situ correction {ref}`C11 <field-c11>`, where an
empty field sets the mark of a borehole TC-score and an unspecified one does not. Neither
writes a flag: {{ decision(14) }}.

```{mermaid}
flowchart TD
    field["One correction field of the child"] --> value{"Its value"}
    value -->|"Present and corrected"| upper["Upper-case letter"]
    value -->|"Present and not corrected"| lower["Lower-case letter"]
    value -->|"Present and not significant"| big_x["X"]
    value -->|"Not recognized"| small_x["x"]
    value -->|"Unspecified or empty"| dash["-"]
    upper --> flags["Seven characters in the order S E T P V C R"]
    lower --> flags
    big_x --> flags
    small_x --> flags
    dash --> flags
```

## Worked examples

The [worked examples](worked-examples.md) give every flag in its position, as present and
corrected and as present and not corrected, each of the other states, a child with no
correction recorded, and children that record all seven.
