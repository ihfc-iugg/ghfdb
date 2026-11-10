# Inherited code

A parent heat-flow value takes its quality code from the children it rests on. The scheme does
not grade a parent on its own. This page describes how the GHFDB portal derives the code. Nothing
in this package computes it yet, and it is part of the scheme because a parent is what a map plots
and what most data users read first.

## Fields read

A parent reads the quality code of each child and whether the child is relevant, which means
that it was used in deriving the parent's value.

{{ fields("C9") }}

## Which children count

* A parent with exactly one child rests on it, whether or not it is marked relevant.
* A parent with several children rests on the children marked `[Yes]`. The children not marked
  take no part, so a poor child stays in the data without lowering the site's
  quality.
* A parent with several children of which none is marked `[Yes]`, or with no children, is not
  determined. Its code is `Ux.Mx.-------`.

Source: Fuchs et al. (2023), Section 3.4 and Fig. 5. The paper passes the score of a single child
"simply" to the parent, and takes the poorest of the children used to derive the parent's value
when there are several. The single child that is not marked relevant is the portal's addition,
because the paper's single-child case does not depend on the mark: {{ decision(9) }}. See
{ref}`DEP-10 <dep-10>`.

## What the parent takes

* **The U-score** is the poorest among the children, ranked `U1`, `U2`, `U3`, `U4`, then `Ux` as
  the poorest.
* **The M-score** is the poorest among the children, ranked `M1` to `M4`, then `M1x` to `M4x`,
  then `Mx` as the poorest. Any grade with the mark is poorer than any grade without it, so `M1x`
  is poorer than `M4`.
* **The perturbation flags** are taken whole from the child with the poorest U-score. When two
  children tie on the U-score, the child with the poorest M-score decides. The flags are not
  merged flag by flag.

The paper says that the poorest ranking is inherited and does not say how the flags are chosen,
or how a grade with the mark ranks against one without it. Both are {{ decision(9) }}.

When two children tie on both scores the portal takes the child it holds first, so that
recalculating gives the same flags every time. What the scheme should say
is under discussion (<https://github.com/ihfc-iugg/ghfdb/issues/40>).

For example, a parent with two relevant children coded `U1.M4.S------` and `U3.M1x.-E-----`
inherits `U3.M1x.-E-----`. `U3` is the poorer U-score, `M1x` is the poorer M-score, and the flags
are those of the child with the poorer U-score.

A parent's value is never changed by inheritance.

```{mermaid}
flowchart TD
    parent["Parent"] --> count{"How many children?"}
    count -->|"None"| none["Ux.Mx.-------"]
    count -->|"One"| single["That child's code"]
    count -->|"Several"| relevant{"Any marked relevant?"}
    relevant -->|"No"| none
    relevant -->|"Yes"| rest["The relevant children"]
    rest --> u["U-score: the poorest"]
    rest --> m["M-score: the poorest, a grade with x counting as poorer"]
    rest --> f["Flags: whole, from the child with the poorest U-score, the poorest M-score breaking a tie"]
    u --> code["Inherited code"]
    m --> code
    f --> code
```

## Worked examples

The [worked examples](worked-examples.md) give a parent with no child, with one child, with
several children and with several of which only some are relevant, each ranking of the U-score
and the M-score, and each way the flags are chosen.

## Under discussion

* <https://github.com/ihfc-iugg/ghfdb/issues/40>: which child's perturbation flags a parent takes when two children tie.
