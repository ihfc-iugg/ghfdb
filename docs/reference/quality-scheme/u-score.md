# U-score

The U-score grades the uncertainty of a child's heat-flow value, from `U1` (excellent) to `U4`
(poor). It is `Ux` when it cannot be determined. This page states the criterion, the fields it
reads and where each rule comes from.

## Fields read

{{ fields("C1", "C2") }}

## The coefficient of variation

The U-score is read from the coefficient of variation, the uncertainty as a percentage of the
value:

```text
coefficient of variation (%) = |C2| / |C1| × 100
```

The coefficient is rounded to six decimal places before it is classed. The sign of either number
is ignored, because a heat flow can be negative: a value of −40 mW/m² with an uncertainty of 12
mW/m² is a coefficient of 30 % and scores `U4`.

| Coefficient of variation | U-score | Description |
|---|---|---|
| Below 5 % | `U1` | Excellent |
| 5 % up to and including 15 % | `U2` | Good |
| Above 15 % up to and including 25 % | `U3` | Ok |
| Above 25 % | `U4` | Poor |

```{mermaid}
flowchart TD
    start["Heat-flow value and its uncertainty"] --> filled{"Both filled and not zero?"}
    filled -->|"No"| ux["Ux, not determined"]
    filled -->|"Yes"| coefficient["Coefficient of variation: the uncertainty as a percentage of the value"]
    coefficient --> classes["The class of the coefficient"]
    classes --> u1["U1"]
    classes --> u2["U2"]
    classes --> u3["U3"]
    classes --> u4["U4"]
```

Source: Fuchs et al. (2023), with its corrigendum (Fuchs et al., 2026, Tectonophysics 934,
231226, <https://doi.org/10.1016/j.tecto.2026.231226>), Section 3.1, Equation 2 and Table 1. The
corrected Table 1 classes a coefficient below 5 % as `U1`, up to 15 % as `U2`, up to 25 % as
`U3` and above 25 % as `U4`, so a coefficient of exactly 15 % is `U2` and one of exactly 25 % is
`U3`. The paper's Equation 2 leaves out the factor of 100 that turns the ratio into a
percentage, and the scheme includes it: see {ref}`DEP-17 <dep-17>`.

## Empty, zero and unspecified

| Input | U-score |
|---|---|
| `C1` empty | `Ux` |
| `C1` zero | `Ux` |
| `C2` empty | `Ux` |
| `C2` zero | `Ux` |

Both fields take numbers only, so neither has an unspecified value. A U-score has no
missing-information mark, so an empty input gives `Ux` and nothing else.

An uncertainty of zero is not determined. Read literally, the paper's equation gives a
coefficient of 0 % for it and so `U1`. The scheme treats it as not determined, as the toolbox
that scored the 2024 release does: see {ref}`DEP-3 <dep-3>`. Source for `Ux`: corrected Table 1,
"not applicable".

## Worked examples

The [worked examples](worked-examples.md) give a child for every class,
for the rounding, for a negative value and for each way a U-score is not determined.
