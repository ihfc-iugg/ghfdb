# Quality scheme

The quality scheme is the set of rules that grades a child heat-flow value. This section states
the whole scheme as the reference for how a child is scored: the U-score, the T-score and
TC-score under the probe-sensing rules and under the borehole and mine rules, the M-score with
its missing-information mark, the perturbation flags and the quality code. It is written for
anyone who needs to know why a child received its grade: data assessors, contributors and
developers who implement the scheme.

The scheme is the one of Fuchs et al. (2023,
[doi:10.1016/j.tecto.2023.229976](https://doi.org/10.1016/j.tecto.2023.229976)) with its
corrigendum (Fuchs et al., 2026, Tectonophysics 934, 231226,
[doi:10.1016/j.tecto.2026.231226](https://doi.org/10.1016/j.tecto.2026.231226)). The corrigendum
corrects the paper's tables, and the pages cite them as "corrected Table 1" to "corrected
Table 3". It says that the corrected scheme accords with version 2026.03 of the submission
template ([doi:10.5880/fidgeo.2025.042](https://doi.org/10.5880/fidgeo.2025.042)) and with
version 0.2 of the data quality code, the Heat Flow Quality Analysis Toolbox (Dergunova et al.
2026, [doi:10.5880/fidgeo.2026.032](https://doi.org/10.5880/fidgeo.2026.032)). Every rule on
these pages names its source, a section, table or figure of the corrected paper. Every place
where the scheme still differs from the corrected paper is listed, with its reasoning, in
[Departures from the paper](departures.md).

This package computes the scores these pages describe and runs the
[worked examples](worked-examples.md) as tests.

```{toctree}
:maxdepth: 1

u-score
probe-sensing
borehole-and-mine
m-score
perturbation-flags
inherited-code
departures
worked-examples
```

## The quality code

A child's quality code joins three parts with full stops, as in `U2.M3x.-e-PX--`.

| Part | In the example | What it grades | Page |
|---|---|---|---|
| U-score | `U2` | The uncertainty of the heat-flow value | [U-score](u-score.md) |
| M-score | `M3x` | The methods used to find the temperature gradient and the thermal conductivity | [M-score](m-score.md) |
| Perturbation flags | `-e-PX--` | Which disturbing effects the authors recognised, and whether they corrected for them | [Perturbation flags](perturbation-flags.md) |

The code has two full stops. The paper writes it with the first one missing: see
{ref}`DEP-1 <dep-1>`. A code is at most fourteen characters long. A code in which
nothing could be determined is `Ux.Mx.-------`.

```{mermaid}
flowchart TD
    child["A child"]
    child --> u["U-score from the heat-flow value and its uncertainty"]
    child --> route{"Exploration method"}
    route -->|"Probing"| probe["Probe-sensing rules give the T-score and the TC-score"]
    route -->|"Drilling, mining, tunnelling, indirect"| borehole["Borehole and mine rules give the T-score and the TC-score"]
    route -->|"Other, unspecified or empty"| none["No rules apply, so the M-score is not determined"]
    probe --> m["M-score from the product of the T-score and the TC-score"]
    borehole --> m
    child --> flags["Perturbation flags from the seven correction fields"]
    u --> code["Quality code"]
    m --> code
    none --> code
    flags --> code
```

A parent takes its quality code from its children. [Inherited code](inherited-code.md) describes
how.

## Which rules score a child

The T-score grades how the temperature gradient was determined and the TC-score how the thermal
conductivity was determined. Two sets of criteria score them, the probe-sensing rules and the
borehole and mine rules. A child is scored by one set, chosen by its exploration method.

{{ fields("P12") }}

| Exploration method | Rules |
|---|---|
| `[Probing (onshore, lake, river, etc.)]`, `[Probing (offshore, ocean)]`, `[Probing (clustered)]` | [Probe sensing](probe-sensing.md) |
| `[Drilling]`, `[Drilling (clustered)]`, `[Mining]`, `[Tunneling]`, `[Indirect (GTM, BSR, CPD, etc.)]` | [Borehole and mine](borehole-and-mine.md) |
| `[Other]`, `[Unspecified]`, or empty | None. The T-score, the TC-score and the M-score are not determined |

Source: Fuchs et al. (2023), Section 3.2, which separates the scheme for shallow probe sensing
from the scheme for borehole and mine data. The paper does not say how a child is assigned to
one of them. The assignment above is {{ decision(17) }}: see {ref}`DEP-6 <dep-6>`. The domain
that each exploration method belongs to is the one the [cross-field rules](../rules.md) use for
the mandatory fields.

Each of a child's two measurements is scored by the rules of its own site. A child whose
gradient and conductivity sit at sites with different exploration methods is scored by two
different sets of rules.

## How a T-score and a TC-score are built

Both scores start at 1.0. Each criterion adds a penalty, which is negative for a worse method
and positive for a better one, and the score is the sum. The scores are rounded to three decimal
places. In practice a T-score or TC-score lies between 0.1 and 1.2. Source: Fuchs et al. (2023),
Section 3.2.

## Empty, unspecified and the missing-information mark

Every criterion reads one or more fields of the child, and a field can hold a value, hold
`[Unspecified]` or be empty. The scheme tells the last two apart.

* **An empty input** takes the criterion's largest penalty and sets the missing-information mark.
  The mark says that the score is a floor, and that the child could score better if the
  information were added.
* **An empty field of a criterion that reads several fields** counts only when no row of the
  criterion holds without it. A row holds whatever the fields it does not name contain, so a row
  that does not name the empty field scores as usual and sets no mark.
* **An input recorded as unspecified** takes the same largest penalty and does not set the mark.
  Nothing is missing: the contributor said the value is not known.
* **A value that fits none of a criterion's classes** takes the largest penalty and does not set
  the mark.

The paper sets the mark for empty and unspecified inputs alike (Section 3.2). The scheme narrows
that to empty inputs: see {ref}`DEP-5 <dep-5>`.

Beyond an empty input, the scheme names these cases that also set the mark:

| Case | Page |
|---|---|
| A borehole conductivity whose interval reports neither a top nor a bottom depth | [Borehole and mine rules](borehole-and-mine.md) |
| A borehole gradient whose temperature methods fit none of the groups of its case | [Borehole and mine rules](borehole-and-mine.md) |
| A borehole conductivity whose location fits none of the three locations | [Borehole and mine rules](borehole-and-mine.md) |
| A borehole child with no in-situ correction recorded | [Borehole and mine rules](borehole-and-mine.md) |

Source: {ref}`DEP-14 <dep-14>` for the three cases of a borehole child that the paper does not
mark. The mark of a T-score or TC-score is carried to the M-score as a trailing `x`, as in
`M3x`. It is never the same thing as `Mx`.

## Not determined

A score that cannot be made is **not determined**. It is written `Ux` for a U-score and `Mx` for
an M-score, and a T-score or TC-score that cannot be made is empty. It is never written as 0.
The T-score and the TC-score are not determined when the exploration method selects no rules,
and when it selects a set of rules and every field they read, other than the exploration method,
is empty. The corrigendum adds the second case to Section 3.2: "If all metadata fields required
for the scoring are missing, the M-score will appear as Mx." The rule is stated at
[M-score](m-score.md). Not determined carries no mark, because nothing was scored and so no
input was missing.

## Several values in one field

A vocabulary field can hold more than one value in the GHFDB portal, such as a gradient with two
temperature methods at its top. The scheme scores every value and takes the poorest. The paper
does not say how to score such a field: {{ decision(8) }}. The upload template holds one value
in each field it scores, so this applies to data held in the portal.

The readings below fill the gaps the paper leaves.

- A number field is scored value by value too. The U-score pairs every value of `C1` with every
  value of `C2`, grades each pair, and takes the poorest pair. A pair with a zero or an empty
  number gives no grade, so a zero among several values is skipped when another pair can be
  graded. The U-score is `Ux` only when no pair can be graded.
- A condition that says every value of a field is among some terms holds only when each value
  is. The probe saturation asks this of the conductivity method for its laboratory rows
  (corrected Table 2).
- Routing by exploration method, the perturbation flags and the two probe waivers read one value:
  the first filled value of the field. The waivers are the tilt correction of `C12` and the
  surface correction of `C17`. The order of the values can therefore change the score.
- A borehole gradient takes its case once for the whole child, not for each value. It is the
  surface case when any top method is the surface. It is a continuous log when every number of
  recordings is more than 3 and every filled method is a continuous log method. Within the
  case, the poorest matching group decides.

## Scores of a child and of its measurements

A child scores its gradient and its conductivity, and applies three rules that read the child's
own corrections:

* the probe tilt criterion is waived when the child's temperature correction `C12` is recorded
  as tilt corrected
* the probe water depth criterion is waived when the child's `C17` is recorded as present and
  corrected
* a borehole conductivity's pT criterion needs the child's in-situ correction `C11` to agree
  with it

The T-score and TC-score of a child include those rules, and the M-score is made from them. The
GHFDB portal also stores a score for each gradient and each conductivity on its own, which reads
nothing from any child, because one measurement can serve several children (the portal's
decisions {{ decision(2) }} and {{ decision(3) }}). The worked examples call those the child's
**own scores** wherever they differ from the child's scores.

## Under discussion

These questions are open with the data assessment team. Until they are settled, the scheme is
written as these pages state it.

* <https://github.com/ihfc-iugg/ghfdb/issues/38>: how the temperature method `[DST]` scores for a borehole gradient.
* <https://github.com/ihfc-iugg/ghfdb/issues/40>: which child's perturbation flags a parent takes when two children tie.
* <https://github.com/ihfc-iugg/ghfdb/issues/42>: how a conductivity measured with the continuous heating probe scores.
* <https://github.com/ihfc-iugg/ghfdb/issues/43>: whether an empty number of temperature recordings sets the mark for a borehole
  gradient.
