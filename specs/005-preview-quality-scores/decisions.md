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
