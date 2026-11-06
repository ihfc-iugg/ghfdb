# Departures from the paper

The scheme starts from the one the GHFDB portal applies today, and the portal follows version 0.2
of the Heat Flow Quality Analysis Toolbox where it and the paper of Fuchs et al. (2023) differ:
{{ decision(1) }}. The toolbox scored the 2024 GHFDB release, so following it keeps the scores
comparable with the scores data users already hold. This page lists every place where the scheme
differs from the paper, or fills a gap the paper leaves. Each entry says what the paper says, what
the scheme does, why, and where the decision is recorded. Each departure is also stated where the
rule lives.

Entries with a number cite the GHFDB portal's decisions, which are linked by their headings. The
rules that the toolbox applies and that the portal's decisions do not list one by one are cited
to the portal's
[research notes](https://github.com/ihfc-iugg/ghfdb-portal/blob/main/specs/007-quality-scores/research.md),
which compare the toolbox's rules with the paper's tables.

The {ref}`questions still open <departures-under-discussion>` are listed at the end of the page.

(dep-1)=
## DEP-1 The quality code has two full stops

* **Paper.** Fig. 4 writes the code as `U1M2.xeTxXcx`, with one full stop.
* **Scheme.** The code is written `U1.M2.xeTxXcx`, with two.
* **Why.** The toolbox's code writes both full stops, and so does the portal.
* **Source.** {{ decision(5) }}.

(dep-2)=
## DEP-2 Heat refraction is R, and the flags follow the order of Fig. 4

* **Paper.** The paper contradicts itself. Its text and Fig. 4 write heat refraction as `R` and
  put surface-temperature variation fifth and convection sixth. Its Table 5 writes `h/H` and swaps
  the fifth and sixth characters.
* **Scheme.** The flags are `S E T P V C R`, as in the text and Fig. 4.
* **Why.** The text, Fig. 4, the website, the release paper and the toolbox agree. Table 5 is the
  outlier.
* **Source.** {{ decision(6) }}. Stated at [Perturbation flags](perturbation-flags.md).

(dep-3)=
## DEP-3 An uncertainty of zero is not determined

* **Paper.** Table 1 classes a coefficient of variation below 5 % as `U1`. Read literally,
  an uncertainty of zero gives a coefficient of 0 % and so `U1`.
* **Scheme.** A value or an uncertainty that is zero gives `Ux`, as does an empty one.
* **Why.** The toolbox does so, and scored the release.
* **Source.** {{ decision(1) }}. Stated at [U-score](u-score.md).

(dep-4)=
## DEP-4 A product on a class boundary takes the better class, after rounding

* **Paper.** Fig. 3 gives the classes as ranges that share their end points, and its worked
  example places an exact 0.25 or 0.50 in the poorer class.
* **Scheme.** The product is rounded to three decimal places and compared with "at least", so a
  product on a boundary takes the better class. A T-score and a TC-score are rounded to three
  decimal places too.
* **Why.** The paper's placements are consistent with floating-point sums such as
  1 − 0.1 − 0.2 − 0.2 = 0.4999…, not with an intended strict inequality. The toolbox rounds and
  compares with "at least".
* **Source.** {{ decision(7) }}. Stated at [M-score](m-score.md).

(dep-5)=
## DEP-5 Only an empty input sets the missing-information mark

* **Paper.** Section 3.2 gives the largest penalty for empty or unspecified fields, and adds an
  `x` to the M-score for both.
* **Scheme.** An empty input takes the largest penalty with the mark. An input recorded as
  unspecified takes the same penalty without the mark.
* **Why.** The toolbox's own test documentation states the narrower rule explicitly. An
  unspecified input is a value the contributor gave.
* **Source.** {{ decision(1) }}. Stated at [the overview](index.md) and at
  [M-score](m-score.md).

(dep-6)=
## DEP-6 A child is routed to a set of rules by its exploration method

* **Paper.** Section 3.2 separates the scheme for probe sensing from the scheme for borehole and
  mine data. It does not say how a child is assigned to one of them, and has no result for a child
  that fits neither.
* **Scheme.** The exploration method `P12` decides: the three probing methods select the
  probe-sensing rules, and drilling, clustered drilling, mining, tunnelling and the indirect
  method select the borehole and mine rules. `[Other]`, `[Unspecified]` and an empty method select
  none, and the M-score is `Mx`.
* **Why.** The scheme needs one set of rules for each child. The toolbox routes by the exploration
  method, and the portal's vocabulary maps onto the toolbox's routing words as stated.
* **Source.** {{ decision(17) }} and {{ decision(1) }}. Stated at [the overview](index.md).
  Whether the mapping of each exploration method to its domain is right is open in
  <https://github.com/ihfc-iugg/ghfdb/issues/36>.

(dep-7)=
## DEP-7 The probe bin edges are the toolbox's, and an elevation at or above sea level has no water depth

* **Paper.** Table 2 gives ranges that share end points. Penetration is "1–3 m" and "<1 m", and
  "3–10 m" and "1–3 m", so a penetration of exactly 1 m or 3 m falls in two rows. The water depth
  is ">1,500 m" and "<1,500 m", so exactly 1500 m falls in none. The paper does not
  consider an elevation at or above sea level.
* **Scheme.** Penetration above 10 m is +0.1, above 3 m is 0, above 1 m is −0.1 and otherwise
  −0.2. Recordings above 5 are +0.1, 3 or more are 0, exactly 2 is −0.1 and otherwise −0.2. A
  water depth of 1500 m or less is −0.2. An elevation of zero or above has no water depth, and the
  criterion is treated as empty.
* **Why.** The toolbox's edges decide, so that exact values land in one class.
* **Source.** {{ decision(1) }}. Stated at [Probe-sensing rules](probe-sensing.md).

(dep-8)=
## DEP-8 The probe tilt waiver reads the temperature correction

* **Paper.** Table 2 waives the tilt penalty when the in-situ correction `corr_IS_flag` is
  `[Tilt corrected]`. It waives the water depth penalty when `corr_BWT_flag` is
  `[Present and corrected]`.
* **Scheme.** The tilt penalty is waived when the temperature correction `C12` `corr_T_flag` is
  `[Tilt corrected]`. The water depth penalty is waived when `C17` `corr_SUR_flag`, the field for
  surface and bottom-water temperature variation, is `[Present and corrected]`.
* **Why.** The toolbox reads the temperature correction, whose vocabulary is the one that holds
  `[Tilt corrected]`. The in-situ correction `C11` takes the values for pressure and temperature
  considered. The portal's vocabulary agrees with the toolbox.
* **Source.** {{ decision(11) }}. Stated at [Probe-sensing rules](probe-sensing.md).

(dep-9)=
## DEP-9 The probe conductivity's saturation criterion has more cases than the paper's table

* **Paper.** Table 2 lists in-situ saturation with the pulse probe, and for laboratory
  measurements saturated measured, saturated calculated and dry measured. `[Recovered]` appears
  only with the pulse probe. The estimates are lithology and literature at a literature
  location (−0.1), and water content or porosity and mineral composition (−0.2).
* **Scheme.** A recovered rock scores 0 with a laboratory method too. A dry, unspecified or other
  saturation scores −0.2 with a laboratory method. The two well-log methods join lithology at
  −0.1, and chlorine content and an unspecified method join the −0.2 estimates. A laboratory
  method is any of the six `[Lab …]` methods. Any empty input of the four the cases name takes
  −0.2 with the mark.
* **Why.** The toolbox's cases decide.
* **Source.** {{ decision(1) }} for the estimation methods, and the portal's research notes for
  the rest. Stated at [Probe-sensing rules](probe-sensing.md).

(dep-10)=
## DEP-10 A parent's code is inherited by the toolbox's ranking

* **Paper.** Section 3.4 and Fig. 5 say that the score of a single child is passed to the parent
  and that the poorest ranking of the relevant children is inherited. They do not say how the
  flags are chosen, or how a grade with the mark ranks against one without it.
* **Scheme.** The U-score ranks `U1` to `U4`, then `Ux`. The M-score ranks `M1` to `M4`, then `M1x`
  to `M4x`, then `Mx`. The flags are taken whole from the child with the poorest U-score, the
  poorest M-score deciding a tie. A parent with one child inherits it whether or not it is marked
  relevant. A parent with several children and none relevant is not determined.
* **Why.** The toolbox's inheritance answers both open points. The single child that is not
  marked relevant is the portal's addition, because the paper's single-child case does not depend
  on the mark.
* **Source.** {{ decision(9) }}. Stated at [Inherited code](inherited-code.md).

(dep-11)=
## DEP-11 A field that holds several values takes the poorest

* **Paper.** Silent about a vocabulary field that holds more than one value.
* **Scheme.** Every value is scored, and the largest penalty wins.
* **Why.** The toolbox does so.
* **Source.** {{ decision(8) }}. Stated at [the overview](index.md).

(dep-12)=
## DEP-12 A borehole gradient is a continuous log only with logging methods

* **Paper.** Table 3 conditions the continuous log on more than three temperature recordings,
  with the logging and distributed-sensing methods, and states no condition for the other two
  cases.
* **Scheme.** A gradient is a continuous log only when it has more than three recordings and
  every method at the top and the bottom is `[LOGeq]`, `[cLOG]`, `[DTSeq]`, `[cDTS]` or
  `[LOGpert]`. Every other gradient is scored as multiple single points, with no condition on the
  count. A method recorded as unspecified or other is scored as an estimate.
* **Why.** The toolbox's cases decide.
* **Source.** {{ decision(1) }}. Stated at [Borehole and mine rules](borehole-and-mine.md).

(dep-13)=
## DEP-13 The borehole groups of methods and values are the toolbox's

* **Paper.** Table 3 lists the temperature methods of each group, some by names that differ from the
  vocabulary's, such as `[ODDT-PC]` and `[RTDc]`. Its
  multiple single points list `[BHT]` and `[DTSeq]` among the equilibrium methods at −0.1. Its
  source and saturation tables list no unspecified and no other value.
* **Scheme.** The groups are those of the vocabulary's names. `[BHT]` is at −0.3 only, and
  `[DTSeq]` is listed for the continuous log only. `[HT-FTeq]`, `[cHT-FT]`, `[EGRT]` and `[GRT]`
  are listed, and `[Unspecified]` and `[Other]` score as estimates. A source or a saturation
  recorded as unspecified or other scores −0.2. A set of methods that fits no group of its case
  takes the case's largest penalty with the mark. The toolbox's misspelled method names are read
  as the vocabulary's `[HT-FTeq]` and `[HT-FTpert]`.
* **Why.** The toolbox's lists decide, and the portal keeps the gaps in them as they are.
* **Source.** {{ decision(1) }}, {{ decision(15) }} and {{ decision(16) }}. Stated at
  [Borehole and mine rules](borehole-and-mine.md). The treatment of `[DST]` and `[cDST]` is
  under discussion (QUESTION-1).

(dep-14)=
## DEP-14 A borehole conductivity with no interval depth carries the mark

* **Paper.** Table 3 ends the scoring with a TC-score of 0.1 when no interval depth is reported,
  and Section 3.2.2.2 gives the penalty as −0.9. It does not mention the mark.
* **Scheme.** The TC-score is 0.1 with the missing-information mark. A borehole conductivity's
  location that fits none of the three values also carries the mark.
* **Why.** An empty input the score needed carries the mark, and the toolbox marks these cases.
* **Source.** {{ decision(1) }}. Stated at [Borehole and mine rules](borehole-and-mine.md).

(dep-15)=
## DEP-15 A borehole conductivity's pT conditions must agree with the in-situ correction

* **Paper.** Table 3 scores the pT conditions on their own: 0 for in-situ conditions, −0.1 for p
  or T alone and −0.2 for ambient or unspecified conditions. It has no rule for the in-situ
  correction `C11` on the borehole side.
* **Scheme.** The pT conditions earn their score only when the child's in-situ correction agrees
  with them. Anything else takes −0.2. A child with no in-situ correction takes −0.2 with the mark.
* **Why.** The toolbox's pT rule needs the in-situ correction, and its worked example with
  corrected pT reaches its expected M-score only with the −0.2. The GHFDB portal also keeps, for
  each measurement, a score that reads the pT conditions on their own terms.
* **Source.** {{ decision(1) }}, {{ decision(3) }} and {{ decision(13) }}. Stated at
  [Borehole and mine rules](borehole-and-mine.md).

(dep-16)=
## DEP-16 The paper's worked examples are not the examples of the scheme

* **Paper.** Table 5 gives worked examples. They contradict the paper's own inputs or rules in
  five places: example F's temperature penalty, example J's U-score, the U-score labelled on
  location 2, location 1's inherited code, which ignores the relevance flags, and example I's
  `M4x` at exactly 0.25.
* **Scheme.** The [worked examples](worked-examples.md) are the output of the toolbox's code for
  each input. Where the toolbox's own tests and its code disagree, the code decides, because it
  scored the release.
* **Why.** An example that contradicts the rules it illustrates cannot test them.
* **Source.** {{ decision(10) }} and {{ decision(12) }}.

(dep-17)=
## DEP-17 The U-score reads magnitudes and a percentage

* **Paper.** Equation 2 writes `COV(%) = HFDunc / HFDmean`, which is a ratio and not a
  percentage. It does not say what a negative value or uncertainty means.
* **Scheme.** The coefficient is the ratio of the magnitudes multiplied by 100, rounded to six
  decimal places. A negative heat flow is legitimate, so its uncertainty is a percentage of the
  value's magnitude.
* **Why.** Table 1's classes are percentages, and a negative value must not be refused.
* **Source.** Fuchs et al. (2023), Table 1, and the
  [edge cases](https://github.com/ihfc-iugg/ghfdb-portal/blob/main/specs/007-quality-scores/spec.md)
  of the portal's specification. Stated at [U-score](u-score.md).

(departures-under-discussion)=
## Under discussion

These places where the paper is ambiguous or contradicts itself, or where the portal's
description and its code disagree, are open with the data assessment team. The scheme is written
as the portal applies it today, and the departures above stand until they are settled.

* QUESTION-1: how the temperature methods `[DST]` and `[cDST]` score for a borehole gradient.
  The portal's description lists them, and its code does not.
* QUESTION-2: whether a borehole conductivity's saturation and pT conditions are scored
  together or apart. The paper's text and its Table 3 describe them differently.
* QUESTION-3: which child's perturbation flags a parent takes when two children tie.
* QUESTION-4: the class of a coefficient of variation of exactly 15 %, which the paper's Table 1
  lists in two classes.
* QUESTION-5: how a conductivity measured with the continuous heating probe scores.
* QUESTION-6: whether an empty number of temperature recordings sets the mark for a borehole
  gradient.
