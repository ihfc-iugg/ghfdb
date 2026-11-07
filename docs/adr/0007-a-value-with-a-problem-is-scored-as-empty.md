# ADR 0007 — A value with a problem is scored as empty

**Status:** accepted

## Decision

When a workbook is checked, its children are scored with the problems the check found. Every cell
named by a problem of the kinds missing, wrong type, out of range, not in vocabulary or rule is
scored as if it were empty. A rule problem blanks the field it names to fill or change, never the
field that made the rule apply. A column problem blanks nothing. The criterion that reads a blanked
cell takes its largest penalty and sets the missing-information mark, and the report says that the
child has problems.

`Dataset.scores()` takes the problem table as an optional argument. Without one, it scores every
value as the scheme's pages say.

## Why

The scheme says what an empty input, an unspecified input and a value that fits none of a
criterion's classes each score, but not what a value the check has rejected scores. A rejected
value carries nothing the scheme can use, and that is what the mark records: the child could score
better once the information is put right. Scoring it as a value that fits no class would take the
same penalty without the mark, and a mistake in the workbook would read as a reported fact.

Keeping the problem table optional lets a developer score data that never came from a workbook,
or that was put right after the check, without a check first.

## Revisit if

The data assessment team rules on how a rejected value scores, or a later scheme version defines
it.
