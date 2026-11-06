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
| Above 15 % up to and including 25 % | `U3` | Acceptable |
| Above 25 % | `U4` | Poor |

```{mermaid}
flowchart TD
    start["Heat-flow value and its uncertainty"] --> filled{"Both filled and not zero?"}
    filled -->|"No"| ux["Ux, not determined"]
    filled -->|"Yes"| coefficient["Coefficient = uncertainty / value × 100"]
    coefficient --> five{"Below 5 %?"}
    five -->|"Yes"| u1["U1"]
    five -->|"No"| fifteen{"15 % or less?"}
    fifteen -->|"Yes"| u2["U2"]
    fifteen -->|"No"| twentyfive{"25 % or less?"}
    twentyfive -->|"Yes"| u3["U3"]
    twentyfive -->|"No"| u4["U4"]
```

Source: Fuchs et al. (2023), Section 3.1, Equation 2 and Table 1. The paper's table gives the
classes as ranges that share their end points. The class of exactly 15 % is under discussion
(QUESTION-4). The scheme classes it as `U2`, which is how the toolbox applies the table:
{{ decision(1) }}. The paper's Equation 2 leaves out the factor of 100 that turns the ratio
into a percentage, and the scheme includes it.

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
coefficient of 0 % for it and so `U1`. The scheme follows the toolbox, which scored the 2024
release and treats it as not determined: {{ decision(1) }}. See {ref}`DEP-3 <dep-3>`.
Source for `Ux`: Fuchs et al. (2023), Table 1, "not applicable".

## Worked examples

The [worked examples](worked-examples.md) give a child for every class,
for the rounding, for a negative value and for each way a U-score is not determined.

## Under discussion

* QUESTION-4: the class of a coefficient of variation of exactly 15 %.
