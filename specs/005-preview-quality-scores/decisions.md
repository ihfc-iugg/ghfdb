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

**Chosen**: the problem kinds missing, wrong type, out of range and not in vocabulary blank the
cell they name. A rule problem and a column problem blank nothing. A column the workbook does not
have is empty for every child already.

**Why**: those four kinds mean the cell holds nothing the scheme can read. A rule problem's value
is a real term that the scheme pages already score, and blanking it would change a score for a
reason the scheme does not give.

## D-4: An out-of-range value scores differently in the report and from Python

**Ambiguous**: the probe tilt criterion gives a tilt below 0° −0.2 without the mark, and the field
schema's range forbids a negative tilt, so the check reports it as out of range.

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
