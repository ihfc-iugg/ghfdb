# Borehole and mine rules

The borehole and mine rules score a child whose exploration method is `[Drilling]`,
`[Drilling (clustered)]`, `[Mining]`, `[Tunneling]` or `[Indirect (GTM, BSR, CPD, etc.)]`. They
give a T-score for the temperature gradient and a TC-score for the thermal conductivity. Both
start at 1.0 and each criterion adds a penalty, as [the overview](index.md) describes, including
what an empty and an unspecified input do.

Source for the whole page: Fuchs et al. (2023), with its corrigendum (Fuchs et al., 2026,
Tectonophysics 934, 231226, <https://doi.org/10.1016/j.tecto.2026.231226>), Section 3.2.2 and
Table 3. Later sources cite the corrigendum's table as "corrected Table 3".

## T-score

The T-score has one criterion, the temperature methods used at the top and the bottom of the
interval, read in one of three cases. Its lowest value is 0.4 and its highest 1.1.

### Fields read

{{ fields("P12", "C31", "C32", "C37") }}

```{mermaid}
flowchart TD
    gradient["Borehole gradient"] --> surface{"Top method includes SUR?"}
    surface -->|"Yes"| case_surface["Surface plus one point: the bottom methods decide"]
    surface -->|"No"| continuous{"Enough recordings and only logging or distributed-sensing methods?"}
    continuous -->|"Yes"| case_continuous["Continuous log"]
    continuous -->|"No"| case_points["Multiple single points"]
    case_surface --> fits{"Do the methods fit a group of the case?"}
    case_points --> fits
    fits -->|"Yes"| poorest["The poorest matching group decides"]
    fits -->|"No"| marked["Largest penalty of the case, with the mark"]
    case_continuous --> sum["T-score = the start value plus the penalty"]
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

Source: corrected Table 3, "Source type and number of T points". The table conditions the
continuous log on more than three recordings (`{T_number} >3`) and the surface case on a top
method of `[SUR]`. It states no condition for the multiple single points. The condition on the
methods of a continuous log and the rule that every other gradient is multiple single points are
{ref}`DEP-12 <dep-12>`.

### Penalties of each case

Within a case, every method the gradient holds at the top and the bottom is matched to its
group, and the poorest matching group decides.

**Continuous log**

{{ criterion('borehole-t.continuous-log') }}

**Multiple single points**

{{ criterion('borehole-t.single-points') }}

**Surface plus one point**, decided by `C32` alone

{{ criterion('borehole-t.surface-plus-one-point') }}

* **Empty.** When both methods are empty, or none of the methods fits a group of the case, the
  gradient takes the empty outcome of the table of its case: the case's largest penalty, with
  the mark.
* **Unspecified.** `[Unspecified]` and `[Other]` are values. They are scored as estimates,
  without the mark, as the corrected table lists `[unspecified]` and
  `[other (specify in comments)]` among the estimated methods.
* **A method that fits no group.** A method listed in none of the groups of its case takes the
  case's largest penalty with the mark: see {ref}`DEP-14 <dep-14>`. `[DTSeq]` and `[cDTS]` are
  listed only for the continuous log, so with three recordings or fewer they fit no group of
  multiple single points. `[DST]` is in the vocabulary and in none of the groups, which is
  under discussion (<https://github.com/ihfc-iugg/ghfdb/issues/38>). `[cDST]` is one of the
  equilibrium or corrected methods of the surface plus one point case.

Source: corrected Table 3. The groups of methods are the table's, written as the vocabulary
writes each method.

## TC-score

The TC-score has a gate and five criteria: the location, the source, the number of conductivity
measurements, the saturation and the pT conditions. Its lowest value is 0.1 and its highest 1.2.

### Fields read

{{ fields("P12", "C4", "C5", "C42", "C41", "C47", "C44", "C45", "C11") }}

```{mermaid}
flowchart TD
    conductivity["Borehole conductivity"] --> depth{"Interval top or bottom reported?"}
    depth -->|"Neither"| gate["Fixed TC-score, with the mark, and nothing else is scored"]
    depth -->|"Yes"| location["Location"]
    depth -->|"Yes"| source["Source"]
    depth -->|"Yes"| literature{"Location literature?"}
    literature -->|"Yes"| skip["Number is not scored"]
    literature -->|"No"| number["Number of measurements"]
    depth -->|"Yes"| saturation["Saturation"]
    depth -->|"Yes"| pt["pT conditions that agree with the in-situ correction"]
    location --> sum["TC-score = the start value plus the penalties"]
    source --> sum
    skip --> sum
    number --> sum
    saturation --> sum
    pt --> sum
```

### Interval depth gate

Reads `C4` `q_top` and `C5` `q_bottom`. When both are empty, the TC-score is the fixed value 0.1
with the mark and no other criterion is scored. When either is filled, the scoring goes on.

Source: corrected Table 3, "Localization": no interval depth ends the scoring with a TC-score of
0.1. The table does not mention the mark. The scheme sets it: see {ref}`DEP-14 <dep-14>`.

### Location

Reads `C42` `tc_location`.

{{ criterion('borehole-tc.location') }}

Source: corrected Table 3, "Localization". A location that fits none of the three carries the
mark: see {ref}`DEP-14 <dep-14>`.

### Source

Reads `C41` `tc_source`.

{{ criterion('borehole-tc.source') }}

`[Unspecified]` and `[Other]` take the penalty of the poorest sources without the mark. Source:
corrected Table 3, "Source type", which lists `[Assumed from literature]`, `[unspecified]` and
`[other (specify in comments)]` together.

### Number of conductivity measurements

Reads `C47` `tc_number`, and `C42` for the exception.

{{ criterion('borehole-tc.number') }}

Source: corrected Table 3, "Number of conductivities", with the condition that the location is
not literature or unspecified. The table gives the penalty for 1 to 15 measurements "or
unspecified", and the scheme adds the mark for an empty number: see {ref}`DEP-5 <dep-5>`.

### Saturation

Reads `C44` `tc_saturation`.

{{ criterion('borehole-tc.saturation') }}

`[Unspecified]` and `[Other]` take the penalty of the poorest saturation without the mark.
Source: corrected Table 3, "Saturation". The text of Section 3.2.2.2 still describes one matrix
of saturation and pT conditions. The corrected tables score them as two criteria, and the scheme
follows the tables.

### Pressure and temperature conditions

Reads `C45` `tc_pT_conditions`, and the child's in-situ correction `C11` `corr_IS_flag`. The
conditions must agree with the correction.

{{ criterion('borehole-tc.pT-agreement') }}

A measurement scored on its own, without a child, reads the pT conditions alone:

{{ criterion('borehole-tc.pT') }}

* **Empty.** When `C45` is empty, or the child records no in-situ correction `C11`, the
  criterion takes the empty outcome of the table.
* **Unspecified.** `[Unspecified]` is a value and takes the penalty of its row without the
  mark.

The in-situ correction is the one criterion of the borehole and mine rules that reads a field
of the child other than the measurement. A conductivity with corrected pT conditions scores the
best penalty only when the child says pressure and temperature were considered. The portal keeps
a score for each measurement that reads the pT conditions alone: {{ decision(3) }}.

Source: corrected Table 3, "pT conditions".

## Worked examples

The [worked examples](worked-examples.md) give a gradient for each of the three cases and each
way a gradient fails to match a group. They give a conductivity for the gate, for every
criterion and for every row of the agreement table. Whole children scored by these rules are the
examples named `X1` to `X5` and `B1` to `B9`.

## Under discussion

* <https://github.com/ihfc-iugg/ghfdb/issues/38>: how the temperature method `[DST]` scores for a borehole gradient. `[cDST]` is settled by the corrected Table 3.
* <https://github.com/ihfc-iugg/ghfdb/issues/43>: whether an empty number of temperature recordings sets the mark for a borehole
  gradient.
