# Borehole and mine rules

The borehole and mine rules score a child whose exploration method is `[Drilling]`,
`[Drilling (clustered)]`, `[Mining]`, `[Tunneling]` or `[Indirect (GTM, BSR, CPD, etc.)]`. They
give a T-score for the temperature gradient and a TC-score for the thermal conductivity. Both
start at 1.0 and each criterion adds a penalty, as [the overview](index.md) describes, including
what an empty and an unspecified input do.

Source for the whole page: Fuchs et al. (2023), Section 3.2.2 and Table 3.

## T-score

The T-score has one criterion, the temperature methods used at the top and the bottom of the
interval, read in one of three cases. Its lowest value is 0.4 and its highest 1.1.

### Fields read

{{ fields("P12", "C31", "C32", "C37") }}

```{mermaid}
flowchart TD
    gradient["Borehole gradient"] --> surface{"Top method includes SUR?"}
    surface -->|"Yes"| case_surface["Surface plus one point: the bottom methods decide, −0.3 to −0.6"]
    surface -->|"No"| continuous{"More than 3 recordings and only logging or distributed-sensing methods?"}
    continuous -->|"Yes"| case_continuous["Continuous log: +0.1, or −0.1 when perturbed"]
    continuous -->|"No"| case_points["Multiple single points: −0.1, −0.3 or −0.5"]
    case_surface --> fits{"Do the methods fit a group of the case?"}
    case_points --> fits
    fits -->|"Yes"| poorest["The poorest matching group decides"]
    fits -->|"No"| marked["Largest penalty of the case, with the mark"]
    case_continuous --> sum["T-score = 1.0 + the penalty"]
    poorest --> sum
    marked --> sum
```

### Which case applies

1. **Surface plus one point**, when `C31` `T_method_top` includes `[SUR]`. Only the methods at
   the bottom, `C32` `T_method_bottom`, decide.
2. **Continuous log**, when `C37` `T_number` is more than 3 and every method at the top and the
   bottom is one of `[LOGeq]`, `[cLOG]`, `[DTSeq]`, `[cDTS]` or `[LOGpert]`.
3. **Multiple single points**, for every other gradient. The number of recordings does not
   matter.

An empty `C37` is not more than 3, so a gradient with an empty number of recordings is never a
continuous log, and the empty number sets no mark (<https://github.com/ihfc-iugg/ghfdb/issues/43>).

Source: Fuchs et al. (2023), Table 3, "Source type and number of T points". The paper conditions
the continuous log on more than three recordings and does not state a condition for the other
cases. The condition on the methods and the rule that every other gradient is multiple single
points are {{ decision(1) }}. See {ref}`DEP-12 <dep-12>`.

### Penalties of each case

Within a case, every method the gradient holds at the top and the bottom is matched to its
group, and the poorest matching group decides.

**Continuous log**

| Penalty | Methods |
|---|---|
| +0.1 | `[LOGeq]`, `[cLOG]`, `[DTSeq]`, `[cDTS]` |
| −0.1 | `[LOGpert]` |

**Multiple single points**

| Penalty | Methods |
|---|---|
| −0.1 | `[LOGeq]`, `[cLOG]`, `[cBHT]`, `[HT-FTeq]`, `[cHT-FT]`, `[RTDeq]`, `[cRTD]`, `[ODTT-PC]`, `[ODTT-TP]`, `[EGRT]`, `[GRT]`, `[cDTS]` |
| −0.3 | `[LOGpert]`, `[DTSpert]`, `[BHT]`, `[HT-FTpert]`, `[RTDpert]`, `[BLK]` |
| −0.5 | `[CPD]`, `[XEN]`, `[GTM]`, `[BSR]`, `[Unspecified]`, `[Other]` |

**Surface plus one point**, decided by `C32` alone

| Penalty | Methods |
|---|---|
| −0.3 | `[cBHT]`, `[RTDeq]`, `[cRTD]`, `[ODTT-PC]`, `[ODTT-TP]`, `[cHT-FT]`, `[EGRT]`, `[GRT]` |
| −0.5 | `[BHT]`, `[HT-FTpert]`, `[RTDpert]` |
| −0.6 | `[CPD]`, `[XEN]`, `[GTM]`, `[BSR]`, `[Unspecified]`, `[Other]` |

* **Empty.** When both methods are empty, or none of the methods fits a group of the case, the
  gradient takes the case's largest penalty with the mark: −0.5 for multiple single points and
  −0.6 for surface plus one point.
* **Unspecified.** `[Unspecified]` and `[Other]` are values. They are scored as estimates,
  without the mark. See {ref}`DEP-12 <dep-12>`.
* **A method that fits no group.** A method listed in none of the groups of its case takes the
  case's largest penalty with the mark. `[DTSeq]` is listed only for the continuous log, so with
  three recordings or fewer it fits no group of multiple single points. `[DST]` and `[cDST]` are
  in the vocabulary and in none of the groups, which is under discussion (<https://github.com/ihfc-iugg/ghfdb/issues/38>). Source:
  {{ decision(16) }}.
* **Spellings.** The toolbox's lists spell three methods in ways the vocabulary does not. They
  are read as the methods they name, `[HT-FTeq]` and `[HT-FTpert]`: {{ decision(15) }}.

Sources: Fuchs et al. (2023), Table 3. The groups of methods are the toolbox's, which name more
methods than the paper: {{ decision(1) }}. See {ref}`DEP-13 <dep-13>`.

## TC-score

The TC-score has a gate and five criteria: the location, the source, the number of conductivity
measurements, the saturation and the pT conditions. Its lowest value is 0.1 and its highest 1.2.

### Fields read

{{ fields("P12", "C4", "C5", "C42", "C41", "C47", "C44", "C45", "C11") }}

```{mermaid}
flowchart TD
    conductivity["Borehole conductivity"] --> depth{"Interval top or bottom reported?"}
    depth -->|"Neither"| gate["TC-score 0.1, with the mark, and nothing else is scored"]
    depth -->|"Yes"| location["Location: actual 0, other −0.1, literature −0.2"]
    depth -->|"Yes"| source["Source: +0.1 down to −0.2"]
    depth -->|"Yes"| literature{"Location literature?"}
    literature -->|"Yes"| skip["Number is not scored"]
    literature -->|"No"| number["Number: more than 15 0, otherwise −0.1"]
    depth -->|"Yes"| saturation["Saturation: 0, −0.1 or −0.2"]
    depth -->|"Yes"| pt["pT conditions that agree with the in-situ correction: 0, −0.1 or −0.2"]
    location --> sum["TC-score = 1.0 + the penalties"]
    source --> sum
    skip --> sum
    number --> sum
    saturation --> sum
    pt --> sum
```

### Interval depth gate

Reads `C4` `q_top` and `C5` `q_bottom`. When both are empty, the TC-score is 0.1 with the mark
and no other criterion is scored. When either is filled, the scoring goes on.

Source: Fuchs et al. (2023), Table 3, "Localization": no interval depth ends the scoring with a
TC-score of 0.1. The paper does not mention the mark. The scheme sets it: {{ decision(1) }}. See
{ref}`DEP-14 <dep-14>`.

### Location

Reads `C42` `tc_location`.

| Location | Penalty |
|---|---|
| `[Actual heat-flow location]` | 0 |
| `[Other location]` | −0.1 |
| `[Literature or unspecified]` | −0.2 |
| Empty, or any other value | −0.2, with the mark |

Source: Fuchs et al. (2023), Table 3, "Localization". The mark for an unmatched value is the
toolbox's: {{ decision(1) }}.

### Source

Reads `C41` `tc_source`.

| Source | Penalty |
|---|---|
| `[In-situ probe]`, `[Core-log integration]` | +0.1 |
| `[Core samples]` | 0 |
| `[Cutting samples]`, `[Outcrop samples]`, `[Well-log interpretation]` | −0.1 |
| `[Mineral computation]`, `[Assumed from literature]`, `[Unspecified]`, `[Other]` | −0.2 |
| Empty | −0.2, with the mark |

`[Unspecified]` and `[Other]` take −0.2 without the mark. Source: Fuchs et al. (2023), Table 3,
"Source type". The paper lists no unspecified and no other source, and the scheme gives them the
penalty of the poorest sources: {{ decision(1) }}. See {ref}`DEP-13 <dep-13>`.

### Number of conductivity measurements

Reads `C47` `tc_number`, and `C42` for the exception.

| Measurements | Penalty |
|---|---|
| More than 15 | 0 |
| 15 or fewer | −0.1 |
| Empty | −0.1, with the mark |

**Not scored.** When `C42` is `[Literature or unspecified]` the criterion is left out.

Source: Fuchs et al. (2023), Table 3, "Number of conductivities", with the condition that the
location is not literature or unspecified. The paper gives −0.1 for 15 or fewer measurements
"or unspecified", and the scheme adds the mark for an empty number.

### Saturation

Reads `C44` `tc_saturation`.

| Saturation | Penalty |
|---|---|
| `[Saturated measured]`, `[Saturated measured in-situ]` | 0 |
| `[Saturated calculated]`, `[Recovered]` | −0.1 |
| `[Dry measured]`, `[Unspecified]`, `[Other]` | −0.2 |
| Empty | −0.2, with the mark |

`[Unspecified]` and `[Other]` take −0.2 without the mark. Source: Fuchs et al. (2023), Table 3,
"Saturation". The paper's text and its table describe this criterion differently, and the scheme
follows the table (<https://github.com/ihfc-iugg/ghfdb/issues/39>). See {ref}`DEP-13 <dep-13>`.

### Pressure and temperature conditions

Reads `C45` `tc_pT_conditions`, and the child's in-situ correction `C11` `corr_IS_flag`. The
conditions must agree with the correction.

| `C45` is | `C11` is | Penalty |
|---|---|---|
| `[Actual in-situ (pT) conditions]`, `[Replicated in-situ (pT)]` or `[Corrected in-situ (pT)]` | `[Pressure and temperature considered]` | 0 |
| `[Replicated in-situ (p)]`, `[Corrected in-situ (p)]`, `[Replicated in-situ (T)]` or `[Corrected in-situ (T)]` | `[Pressure considered]` or `[Temperature considered]` | −0.1 |
| `[Recorded ambient pT conditions]`, `[Unrecorded ambient pT conditions]` or `[Unspecified]` | `[Not considered]` or `[Unspecified]` | −0.2 |
| any other combination | | −0.2 |

* **Empty.** When `C45` is empty, or the child records no in-situ correction `C11`, the criterion
  takes −0.2 with the mark.
* **Unspecified.** `[Unspecified]` is a value and takes −0.2 without the mark.

The paper scores the pT conditions on their own, with 0 for in-situ conditions, −0.1 for p or T
alone and −0.2 for ambient or unspecified conditions, and has no rule for the in-situ
correction. The scheme requires the agreement, so a conductivity with corrected pT conditions
scores 0 only when the child says pressure and temperature were considered: {{ decision(1) }},
{{ decision(3) }} and {{ decision(13) }}. See {ref}`DEP-15 <dep-15>`. The in-situ correction is
the one criterion of the borehole and mine rules that reads a field of the child other than the
measurement.

Source: Fuchs et al. (2023), Table 3, "pT conditions".

## Worked examples

The [worked examples](worked-examples.md) give a gradient for each of the three cases and each
way a gradient fails to match a group. They give a conductivity for the gate, for every
criterion and for every row of the agreement table. Whole children scored by these rules are the
examples named `X1` to `X5` and `B1` to `B9`.

## Under discussion

* <https://github.com/ihfc-iugg/ghfdb/issues/38>: how the temperature methods `[DST]` and `[cDST]` score for a borehole gradient.
* <https://github.com/ihfc-iugg/ghfdb/issues/39>: whether a borehole conductivity's saturation and pT conditions are scored
  together or apart.
* <https://github.com/ihfc-iugg/ghfdb/issues/43>: whether an empty number of temperature recordings sets the mark for a borehole
  gradient.
