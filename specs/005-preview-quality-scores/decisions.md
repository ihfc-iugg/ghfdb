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

## D-2: The open questions of the scheme do not block scoring

**Ambiguous**: issues #30 to #43 hold open questions about the scheme, and some of them may change
how a child scores.

**Chosen**: the code follows the scheme pages as they read today. When a question is settled, the
change to the page, its worked examples and the code lands together and is recorded under
**Scheme changes** in the changelog (FR-013).

**Why**: the pages already state a definite reading for each open question, and the worked
examples test it. Waiting would hold the feature on rulings with no date.

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

## D-5: Scoring works on whole columns

**Chosen**: each criterion is scored for every child at once with pandas, and a field with several
values is held as one row per value. See `research.md`, "Approach".

**Why**: SC-004. One Python call per child per criterion would use most of the time left in the
15-second budget.

## D-6: Several values reach the scoring only from a dataset built in code

**Ambiguous**: the scheme scores every value of a field that holds several and takes the poorest,
and four worked examples give one (PC-12, BT-14, BC-38, B5-drilling-clustering). The field schema
gives none of the scored fields a separator, so a workbook cell holds one value.

**Chosen**: a cell of a dataset that holds a Python list holds several values, in any scored field.
Text is never split for a scored field.

**Why**: the scheme's overview says the upload template holds one value in each field it scores,
and that several values come from data held elsewhere. Splitting text by a separator the schema
does not declare would score a workbook differently from how the check reads it.

## D-7: Routing and the flags read a field's first value

**Ambiguous**: the scheme scores every value of a field that holds several and takes the poorest,
but routing and the perturbation flags are not penalties, so there is no poorest to take.

**Chosen**: routing reads the first filled value of the exploration method, and each flag reads the
first filled value of its correction field. Every criterion that gives a penalty keeps the
poorest.

**Why**: the upload template holds one value in each of these fields, and the scheme says nothing
about several. Taking the first is the plainest reading until it does.

**ADR:** none. It is local to this feature and changes with the scheme page if a ruling covers it.
