# M-score

The M-score grades the methods used to find a child's heat-flow value, from `M1` (excellent) to
`M4` (poor). It is made from the child's T-score and TC-score, which the
[probe-sensing rules](probe-sensing.md) or the [borehole and mine rules](borehole-and-mine.md)
give. An `x` after the grade, as in `M3x`, is the missing-information mark. `Mx` means the
M-score is not determined, which is a different thing.

## Inputs

The M-score reads the child's T-score and TC-score, with the effect of the child's own
corrections already included, and whether either carries the mark. It reads no field directly.

## The product and its classes

The M-score is the class of the product of the T-score and the TC-score, rounded to three
decimal places.

| Product | M-score | Description |
|---|---|---|
| 0.75 or more | `M1` | Excellent |
| 0.50 or more, below 0.75 | `M2` | Good |
| 0.25 or more, below 0.50 | `M3` | Acceptable |
| Below 0.25 | `M4` | Poor |

A product exactly on a boundary takes the better class. The paper's figure gives the classes
as ranges that share their end points, and the paper's own example places an exact 0.25 or 0.50
in the poorer class. That is consistent with floating-point sums such as 1 − 0.1 − 0.2 − 0.2 =
0.4999…, and not with an intended strict inequality: {{ decision(7) }}.

Source: Fuchs et al. (2023), Section 3.2 and Fig. 3, whose legend gives the boundaries 0.75, 0.50
and 0.25. The rounding of the product is {{ decision(1) }}. See {ref}`DEP-4 <dep-4>`.

```{mermaid}
flowchart TD
    scores["T-score and TC-score of the child"] --> determined{"Both determined?"}
    determined -->|"No"| mx["Mx, not determined"]
    determined -->|"Yes"| product["Product, rounded"]
    product --> classes["The class of the product"]
    classes --> g1["M1"]
    classes --> g2["M2"]
    classes --> g3["M3"]
    classes --> g4["M4"]
    g1 --> marked{"Either score carries the mark?"}
    g2 --> marked
    g3 --> marked
    g4 --> marked
    marked -->|"Yes"| x["Add x, as in M3x"]
    marked -->|"No"| plain["Grade as it is"]
```

## The missing-information mark

When the T-score or the TC-score, or both, carries the mark, an `x` follows the grade: `M1x`
to `M4x`. The grade itself is not changed, because each criterion that lacked information took
its largest penalty already. The mark says that the child could grade better if the missing
information were added. [The overview](index.md) lists what sets the mark.

Source: Fuchs et al. (2023), Section 3.2, where the `x` marks incomplete data, and the note
under Fig. 3. The paper sets the mark for empty and unspecified inputs, and the scheme sets it
for empty inputs only: {{ decision(1) }}. See {ref}`DEP-5 <dep-5>`.

## Not determined

The M-score is `Mx` when the T-score or the TC-score is not determined, whether or not the other
carries the mark. That happens when the exploration method is `[Other]`, `[Unspecified]` or empty,
which selects no rules, and when the GHFDB portal holds no gradient or no conductivity for the
child. It is never written as `M4`.

Source: Fuchs et al. (2023), Fig. 3, which has no class for a child that cannot be scored, and
{{ decision(1) }} for routing. See {ref}`DEP-6 <dep-6>`.

## Worked examples

The [worked examples](worked-examples.md) give a product in every class, products on each
boundary, the rounding, each way the mark is set and each way the M-score is not determined.
