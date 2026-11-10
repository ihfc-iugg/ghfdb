# Decisions: Preview quality scores for each child

## D-1: An input with a problem is scored as if it were empty

**Ambiguous**: a child can have problems and still be scored. The scheme says what an empty input,
an unspecified input and a value fitting no class each score, but not what a value the check
rejected scores.

**Chosen**: it is scored as if it were empty. Its criterion takes the largest penalty and the
missing-information mark is set, and the child's row of scores says that it has problems.

**Why**: a rejected value carries no information the scheme can use, which is what the mark
records. Scoring it as a value fitting no class would take the same penalty without the mark, and
would let a mistake in the workbook pass as a reported fact. Agreed when the feature was scoped.

**ADR:** docs/adr/0008-a-value-with-a-problem-is-scored-as-empty.md

## D-2: The open questions of the scheme do not block scoring

**Ambiguous**: issues #30 to #43 hold open questions about the scheme, and some of them may change
how a child scores.

**Chosen**: the code follows the scheme pages as they read today. When a question is settled, the
change to the page, its worked examples and the code lands together and is recorded under
**Scheme changes** in the changelog (FR-013).

**Why**: the pages already state a definite reading for each open question, and the worked
examples test it. Waiting would hold the feature on rulings with no date.

**ADR:** none. It is a sequencing call for this feature; each ruling lands as its own change.

## D-3: Which problems blank a cell

**Ambiguous**: D-1 says an input with a problem is scored as empty. A rule problem names a field
too, but its value is a valid one that does not fit with another field.

**Chosen**: every problem kind that names a cell blanks it: missing, wrong type, out of range, not
in vocabulary and rule. A rule problem blanks the field it names to fill or change (`code`), never
the field that made the rule apply (`related`). A column problem blanks nothing: a column the
workbook does not have is empty for every child already.

**Why**: FR-005 says an input with a problem is scored as empty, and a rule problem is a problem
with the field it names. The field in `related` is correct as it stands; it is what makes the other
one wrong.

**ADR:** docs/adr/0008-a-value-with-a-problem-is-scored-as-empty.md

## D-4: An out-of-range value scores differently in the report and from Python

**Ambiguous**: the probe tilt criterion gives a tilt below 0° −0.2 without the mark, and the field
schema's range forbids a negative tilt, so the check reports it as out of range. The same holds for
any value the scheme scores that the field schema's range rejects, such as a negative uncertainty
`C2`, whose sign the U-score ignores.

**Chosen**: the report follows D-1 and scores it as empty, with the mark. `Dataset.scores()`
without a problem table scores the value as the page says, without the mark.

**Why**: both follow from rules already agreed: D-1 for a checked workbook, and the scheme page for
a value given directly. The report's row says the child has problems, so the mark there is
explained.

**ADR:** none. It follows from ADR 0008 and needs no record of its own.

## D-5: Scoring works on whole columns

**Chosen**: each criterion is scored for every child at once with pandas, and a field with several
values is held as one row per value. See `research.md`, "Approach".

**Why**: SC-004. One Python call per child per criterion would use most of the time left in the
15-second budget.

**ADR:** none. It is an implementation choice inside the scoring modules, visible in the code.

## D-6: Several values reach the scoring only from a dataset built in code

**Ambiguous**: the scheme scores every value of a field that holds several and takes the poorest,
and four worked examples give one (PC-12, BT-14, BC-38, B5-drilling-clustering). The field schema
gives none of the scored fields a separator, so a workbook cell holds one value.

**Chosen**: a cell of a dataset that holds a Python list holds several values, in any scored field.
Text is never split for a scored field.

**Why**: the scheme's overview says the upload template holds one value in each field it scores,
and that several values come from data held elsewhere. Splitting text by a separator the schema
does not declare would score a workbook differently from how the check reads it.

**ADR:** docs/adr/0009-several-values-come-only-from-python.md

## D-7: Routing and the flags read a field's first value

**Ambiguous**: the scheme scores every value of a field that holds several and takes the poorest,
but routing and the perturbation flags are not penalties, so there is no poorest to take.

**Chosen**: routing reads the first filled value of the exploration method, and each flag reads the
first filled value of its correction field. Every criterion that gives a penalty keeps the
poorest.

**Why**: the upload template holds one value in each of these fields, and the scheme says nothing
about several. Taking the first is the plainest reading until it does.

**ADR:** none. It is local to this feature and changes with the scheme page if a ruling covers it.

## D-8: A borehole gradient's case is chosen once for the child

**Ambiguous**: the borehole and mine T-score reads one of three cases, and the page chooses the case
from the methods and the number of recordings. It does not say how to choose when a field holds
several values.

**Chosen**: the case is chosen for the child, not for each value. It is surface plus one point when
any top method is `[SUR]`, as the page's "includes" reads. It is a continuous log when every
number of recordings is more than 3 and every filled method is in the continuous list. Within the
case, the poorest matching group decides, as the page says.

**Why**: a case describes how the whole gradient was measured, so it belongs to the child. Several
numbers of recordings reach the scoring only from a dataset built in Python (D-6), and requiring
every one to exceed 3 is the reading that never grades a gradient better than its poorest value.

**ADR:** none. It is local to this feature and follows the scheme page if a ruling covers it.

## D-9: A worked example can break a cross-field rule

**Found**: the worked example `B9-everything-unspecified` gives a conductivity location of
`[Literature or unspecified]` with a source of `[Unspecified]`. Cross-field rule CF-3 allows that
location only when the source is assumed from literature, so a workbook holding this child has a
rule problem on `C41`. Under D-3 the report scores `C41` as empty, and the M-score is `M4x` where
the example gives `M4`.

**Chosen**: the example is scored as written through `Dataset.scores()`, where it passes, and the
report test for the worked examples leaves it out and checks instead that the report agrees with
`Dataset.scores(problems=…)` for it.

**Why**: both outcomes follow from rules already agreed: the scheme scores the inputs it is given,
and the report scores a value with a problem as empty (FR-005). Whether `[Unspecified]` should
satisfy CF-3 is a question for the cross-field rules, not for scoring.

**ADR:** none. It is local to this feature's tests.

## D-10: The scheme follows the corrected paper

**Found**: Fuchs et al. (2023) has a 2026 corrigendum (Tectonophysics 934, 231226) with corrected
Tables 1 to 5 and Appendices A and B, and a sentence added to Section 3.2. The scheme pages were
written from the 2023 tables and the toolbox's code.

**Chosen**: the scheme follows the corrected paper. Where the corrected tables and the toolbox
agree, the rule is the paper's and is no longer a departure. Where they still disagree, the
corrected paper decides, unless a departure that stays on the departures page says otherwise.

**Why**: the corrigendum states that the corrected scheme accords with version 2026.03 of the
template and with version 0.2 of the toolbox, so it is the published statement of the scheme as of
2026. Agreed with Sam at the plan gate on 2026-11-10.

**ADR:** none. It is the scheme's source, recorded on the departures page and in the changelog.

## D-11: Every scored field empty gives Mx

**Found**: the corrigendum adds to Section 3.2: "If all metadata fields required for the scoring
are missing, the M-score will appear as Mx."

**Chosen**: when a child is routed to a set of rules and every field those rules read, other than
the exploration method, is empty, the T-score and TC-score are not determined and the M-score is
`Mx`. The same holds for the child's own scores.

**Why**: `Mx` already means that a T-score or TC-score is not determined, so reading the new
sentence as "nothing could be scored" keeps one meaning for `Mx`. Showing a T-score of 0.5 beside
`Mx` would contradict it. The exploration method is left out because it decides which fields are
required, and a child without one is `Mx` already.

**ADR:** none. Stated on the M-score page with a worked example for each set of rules.

## D-12: `[cDTS]` is not a multiple single point, and `[cDST]` is a corrected single point

**Found**: the corrected Table 3 lists `[LOGeq]`, `[cLOG]`, `[cBHT]`, `[HT-FTeq]`, `[cHT-FT]`,
`[RTDeq]`, `[cRTD]`, `[ODTT-PC]`, `[ODTT-TP]`, `[EGRT]` and `[GRT]` as equilibrium or corrected
multiple single points. The 2023 table also listed `[DTSeq]` and `[cDTS]`, and the corrigendum
took them out together. The toolbox still lists `[cDTS]`. For surface plus one point, the corrected
table lists `[cDST]` with the corrected methods, and the vocabulary still publishes it.

**Chosen**: `[cDTS]` is in no group of multiple single points, so with three recordings or fewer it
takes the case's largest penalty with the mark, as `[DTSeq]` does. `[cDST]` scores −0.3 at the
bottom of a surface-plus-one-point gradient. `[DST]` stays in no group.

**Why**: D-10. Distributed temperature sensing is a continuous measurement, which is how the
corrigendum treats both `[DTSeq]` and `[cDTS]`.

**ADR:** none. Recorded under **Scheme changes**.

## D-13: A probe laboratory case needs every method to be a laboratory method

**Found**: the corrected Table 2 adds the condition "`{tc_method}` is all with `[Lab - ...]`" to
the onshore laboratory rows of the saturation criterion, and lists `[Other]` among the −0.2
estimates.

**Chosen**: the laboratory rows hold only when every value of `C43` is a laboratory method.
`[Other]` is listed with the −0.2 estimates.

**Why**: D-10. The condition matters only for several values, which come only from a dataset built
in code (D-6). `[Other]` already scored −0.2 as a value that fits no row, so its score does not
change.

**ADR:** none.

## D-14: Each criterion is declared once, and code names fields by column name

**Ambiguous**: Sam judged the first implementation unmaintainable: a criterion's concepts, penalty
table and thresholds were spread over several modules and written several ways, and fields were
named by their codes.

**Chosen**: each criterion is one declaration of three kinds of table, the scheme pages render
their tables from the declarations, and Python source names a field by its published column name
through the generated `Field`. The data stays keyed by field code.

**Why**: the cross-field rules already work this way (ADR 0006), and a declaration the docs render
cannot drift from its page. Keying the data by column name instead would break `Dataset.data`
(ADR 0005) and every worked example, and make each correction of a column name a breaking change.
Agreed with Sam at the plan gate on 2026-11-10.

**ADR:** docs/adr/0010-each-scheme-criterion-is-declared-once.md

## D-15: The 15-second figure is a target

**Ruled**: Sam, 2026-11-10: "accuracy and quality are our two biggest drivers. The 15s target is
aspirational. We should not be sacrificing code readability, maintainability, etc for the sake of a
few extra seconds off the clock."

**Chosen**: SC-004 is a target. The speed test keeps its assertions that every child is checked,
scored and reported, and fails on time only at a ceiling well above the target, so that it catches a
slowdown by a large factor but never a design chosen for clarity.

**Why**: the ruling. A limit set at the target fails on a loaded machine with no change to the code,
and would push every design towards speed.

**ADR:** none.

## D-16: An empty field counts only when no row of the criterion holds without it

**Found**: in review. A criterion of several fields gave its empty outcome, the largest penalty
with the mark, whenever any field it reads was empty, even when the row that applies does not name
that field. A laboratory conductivity with an empty source scored −0.2 for its saturation, where
the corrected Table 2 gives 0, and the worked example `PC-10` expects 0.7 where the table gives 1.0.

**Chosen**: a row holds when every field it names holds one of its concepts, whatever the fields it
does not name hold. The empty outcome applies only when no row holds and a field some row names is
empty. When no row holds and nothing is empty, the unmatched outcome applies as before.

**Why**: D-10. The corrected tables condition each row on the fields it names, and nothing in them
makes an unnamed field matter. The behaviour came from the toolbox and is listed in none of its
decisions, so it was not a departure the scheme chose.

**ADR:** none. Recorded under **Scheme changes**, with the worked examples it changes.
