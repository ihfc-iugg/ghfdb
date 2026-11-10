# Departures from the paper

The scheme follows Fuchs et al. (2023), with its corrigendum (Fuchs et al., 2026,
Tectonophysics 934, 231226, <https://doi.org/10.1016/j.tecto.2026.231226>). The corrigendum
corrects the paper's Tables 1 to 5, and says that the corrected scheme accords with version
2026.03 of the submission template and with version 0.2 of the data quality code, the Heat Flow
Quality Analysis Toolbox. Where a corrected table gives a rule, the scheme applies it, and the
page that states the rule cites the table. This page lists the places where the scheme still
differs from the corrected paper, or fills a gap the paper leaves. Each departure says what the
paper says, what the scheme does, why, and where the decision is recorded. Each departure is
also stated where the rule lives.

Entries with a source cite the GHFDB portal's decisions, which are linked by their headings.

The {ref}`questions still open <departures-under-discussion>` are listed at the end of the page.

(dep-1)=
## DEP-1 The quality code has two full stops

* **Paper.** Fig. 4 and Table 5 write the code with one full stop, as in `U1M2.xeTxXcx`.
* **Scheme.** The code is written `U1.M2.xeTxXcx`, with two.
* **Why.** The toolbox writes both full stops, and so does the portal.
* **Source.** {{ decision(5) }}.

(dep-2)=
## DEP-2 Heat refraction is R, and the flags follow the order of Fig. 4

* **Paper.** The corrected paper still contradicts itself. Its text and Fig. 4 write heat
  refraction as `R` and put surface-temperature variation fifth and convection sixth. Its Table 5
  writes `h/H` and swaps the fifth and sixth characters.
* **Scheme.** The flags are `S E T P V C R`, as in the text and Fig. 4.
* **Why.** The text, Fig. 4, the website, the release paper and the toolbox agree. Table 5 is the
  outlier.
* **Source.** {{ decision(6) }}. Stated at [Perturbation flags](perturbation-flags.md).

(dep-3)=
## DEP-3 An uncertainty of zero is not determined

* **Paper.** Corrected Table 1 classes a coefficient of variation below 5 % as `U1`. Read
  literally, an uncertainty of zero gives a coefficient of 0 % and so `U1`.
* **Scheme.** A value or an uncertainty that is zero gives `Ux`, as does an empty one.
* **Why.** The toolbox does so, and scored the 2024 release.
* **Source.** Stated at [U-score](u-score.md).

(dep-4)=
## DEP-4 The scores and their product are rounded to three decimal places

* **Paper.** Fig. 3 gives the thresholds 0.75, 0.5 and 0.25, and the corrigendum places a product
  of exactly 0.25 in `M3`. The paper states no rounding.
* **Scheme.** A T-score, a TC-score and their product are rounded to three decimal places before
  the product is classed.
* **Why.** A sum of tenths such as 1 − 0.1 − 0.2 − 0.2 is 0.4999… in floating point. Rounding
  keeps a product that is exactly on a threshold from falling below it. The toolbox rounds too.
* **Source.** {{ decision(7) }}. Stated at [M-score](m-score.md).

(dep-5)=
## DEP-5 Only an empty input sets the missing-information mark

* **Paper.** Section 3.2 gives the largest penalty for empty or unspecified fields, and adds an
  `x` to the M-score for both. The corrigendum leaves this text as it was, and its Table 5 sets
  the mark for an unspecified pT condition in some examples and not in others.
* **Scheme.** An empty input takes the largest penalty with the mark. An input recorded as
  unspecified takes the same penalty without the mark.
* **Why.** An unspecified input is a value the contributor gave, and an empty one is
  information that is missing. The toolbox applies the narrower rule.
* **Source.** Stated at [the overview](index.md) and at [M-score](m-score.md).

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
* **Source.** {{ decision(17) }}. Stated at [the overview](index.md). Whether the mapping of each
  exploration method to its domain is right is open in
  <https://github.com/ihfc-iugg/ghfdb/issues/36>.

(dep-7)=
## DEP-7 An elevation at or above sea level has no water depth

* **Paper.** Corrected Table 2 reads the water depth of a probe from the elevation, and gives
  penalties for depths of more than 1,500 m and more than 2,500 m. It does not consider an
  elevation at or above sea level.
* **Scheme.** An elevation of zero or above has no water depth, and the criterion is treated as
  empty: the largest penalty with the mark, unless the bottom-water correction waives it.
* **Why.** The table's depths are depths below sea level, so there is no value to score, which is
  what an empty input is.
* **Source.** Stated at [Probe-sensing rules](probe-sensing.md).

(dep-8)=
## DEP-8 The probe waivers read the temperature correction and the surface flag

* **Paper.** Corrected Table 2 waives the tilt penalty when the in-situ correction
  `{corr_IS_flag}` is `[Tilt corrected]`, and the water depth penalty when `{corr_BWT_flag}` is
  `[Present and corrected]`. The template has no field `corr_BWT_flag`, and the vocabulary of the
  in-situ correction has no `[Tilt corrected]`.
* **Scheme.** The tilt penalty is waived when the temperature correction `C12` `corr_T_flag` is
  `[Tilt corrected]`. The water depth penalty is waived when `C17` `corr_SUR_flag`, the field for
  surface and bottom-water temperature variation, is `[Present and corrected]`.
* **Why.** The vocabulary of the temperature correction is the one that holds `[Tilt corrected]`.
  The in-situ correction `C11` takes the values for pressure and temperature considered. The
  paper's Appendix B calls `C17` the flag for surface and bottom-water temperature.
* **Source.** {{ decision(11) }}. Stated at [Probe-sensing rules](probe-sensing.md).

(dep-10)=
## DEP-10 A parent's code is inherited by a ranking the paper does not give

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
* **Why.** One good value then never hides a poor one. The toolbox does so.
* **Source.** {{ decision(8) }}. Stated at [the overview](index.md).

(dep-12)=
## DEP-12 A borehole gradient is a continuous log only with the methods of a continuous log

* **Paper.** Corrected Table 3 conditions the continuous log on more than three temperature
  recordings (`{T_number} >3`) and lists its methods. It states no condition for the multiple
  single points.
* **Scheme.** A gradient is a continuous log only when it has more than three recordings and
  every method at the top and the bottom is `[LOGeq]`, `[cLOG]`, `[DTSeq]`, `[cDTS]` or
  `[LOGpert]`. Every other gradient is scored as multiple single points, with no condition on
  the count.
* **Why.** The scheme needs one case for each gradient, and the table states a condition for the
  continuous log only.
* **Source.** Stated at [Borehole and mine rules](borehole-and-mine.md).

(dep-14)=
## DEP-14 Some borehole scores carry the mark where the paper gives none

* **Paper.** Corrected Table 3 ends the scoring with a TC-score of 0.1 when no interval depth is
  reported, and Section 3.2.2.2 gives the penalty as −0.9. The table does not mention the mark
  for it, for a location that fits none of the three, or for a temperature method that fits no
  group of its case.
* **Scheme.** The TC-score of 0.1 carries the missing-information mark. So does a borehole
  conductivity's location that fits none of the three values. A gradient whose methods fit no
  group of its case takes the case's largest penalty with the mark.
* **Why.** An empty input the score needed carries the mark, and these are inputs the table could
  not score. The toolbox marks these cases.
* **Source.** {{ decision(16) }}. Stated at [Borehole and mine rules](borehole-and-mine.md).

(dep-16)=
## DEP-16 Table 5 of the corrected paper contradicts its own inputs and rules

* **Paper.** Table 5 gives worked examples, and the corrigendum corrected several. It still
  contradicts Table 1 and its inputs in places:
  * It gives `U3` to examples B and C, whose uncertainty ratios are 3.1 % and 3.8 %, and to H, I
    and J, whose ratios are 5.0 %, 10.4 % and 8.8 %. Table 1 makes these `U1` and `U2`.
  * It sets the mark for an unspecified pT condition in the probe examples B and C, and not in
    the borehole examples G, I and J.
  * Its probe T-scores are 0.2 lower than the scheme's, because it applies the water depth
    penalty where `C17` is `[Present and corrected]`.
  * Well 3's inherited code is `M4`, although none of its children is, and one probe location's
    inherited code ignores the relevance flags.
  * Example I's erosion flag is written `r`, the letter of heat refraction.
  * In the probe columns, the method rows and the flag rows belong to different examples.
* **Scheme.** The [worked examples](worked-examples.md) are the scores the rules of the scheme
  give each input. Where Table 5 and the rules disagree, the rules decide.
* **Why.** An example that contradicts the rules it illustrates cannot test them.
* **Source.** {{ decision(10) }}.

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

These places where the paper is ambiguous or contradicts itself are open with the data
assessment team. The scheme is written as the departures above state it, and they stand until
the questions are settled.

* <https://github.com/ihfc-iugg/ghfdb/issues/38>: how the temperature method `[DST]` scores for a borehole gradient.
  The corrected Table 3 lists `[cDST]`, which is settled, and replaces `[DST]` by `[HT-FT]`, and the
  vocabulary still publishes `[DST]`.
* <https://github.com/ihfc-iugg/ghfdb/issues/40>: which child's perturbation flags a parent takes when two children tie.
* <https://github.com/ihfc-iugg/ghfdb/issues/42>: how a conductivity measured with the continuous heating probe scores.
* <https://github.com/ihfc-iugg/ghfdb/issues/43>: whether an empty number of temperature recordings sets the mark for a borehole
  gradient.
