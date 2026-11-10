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

A product exactly on a boundary takes the better class. The corrigendum states the thresholds
as lower thresholds, at 0.75 for `M1`, 0.5 for `M2` and 0.25 for `M3`, and its Fig. 3 places the
product of a T-score of 0.5 and a TC-score of 0.5 in `M3`.

Source: Fuchs et al. (2023), with its corrigendum (Fuchs et al., 2026, Tectonophysics 934,
231226, <https://doi.org/10.1016/j.tecto.2026.231226>), Section 3.2 and Fig. 3, whose legend
gives the thresholds. The paper does not say that the product is rounded. The scheme rounds it
to three decimal places before it is classed, so that a sum of penalties such as
1 − 0.1 − 0.2 − 0.2 = 0.4999… is not placed below the boundary by floating-point error: see
{ref}`DEP-4 <dep-4>` and {{ decision(7) }}.

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
for empty inputs only: see {ref}`DEP-5 <dep-5>`.

## Not determined

The M-score is `Mx` when the T-score or the TC-score is not determined, whether or not the other
carries the mark. That happens in three cases:

* The exploration method is `[Other]`, `[Unspecified]` or empty, which selects no rules.
* The GHFDB portal holds no gradient or no conductivity for the child.
* The exploration method selects a set of rules, and every field those rules read, other than
  the exploration method, is empty.

It is never written as `M4`.

Source: for the last case, the sentence that the corrigendum adds at the end of Section 3.2: "If
all metadata fields required for the scoring are missing, the M-score will appear as Mx." The
scheme reads it as above: a child with nothing the rules could score has no T-score and no
TC-score, and so no M-score, which is what `Mx` already means. The other two cases are
{ref}`DEP-6 <dep-6>`, and the paper's Fig. 3 has no class for a child that cannot be scored.

## Worked examples

The [worked examples](worked-examples.md) give a product in every class, products on each
boundary, the rounding, each way the mark is set and each way the M-score is not determined.
