# Decisions: Check a workbook and get a report of every problem

Choices made while specifying, where the request was silent. Each can be overruled at review.

## D-1 — A number stored as text is checked as that number

Excel often stores a typed number as text, for example after a paste from a PDF. When the text
reads exactly as a number, such as `12.5`, the check treats it as that number and reports nothing.
Article XII forbids changing, coercing or dropping a value without a problem, and nothing here is
changed: the value is the one the assessor typed, and only the kind of cell differs. Reporting
these would fill a report with problems an assessor cannot act on in the data.

Text that is a number only once something is removed or replaced (`1,234.5`, `12,5`, `60 mW`) is
reported as wrong type. Reading it as a number would mean guessing which separator was meant, which
is exactly the silent coercion the old checking tool was faulted for.

## D-2 — A date cell in a year-and-month field is wrong type

Excel turns `2020-05` typed into a cell into a full date unless the cell is formatted as text.
The check reports such a cell as wrong type rather than reading its year and month, because the cell
holds a day the assessor never entered and the field schema's format is a year and month. If this
turns out to be common in real workbooks, the upload template can format those columns as text,
which fixes it at the source.

## D-3 — Domain-only obligation waits for the cross-field rules

Five fields are mandatory for one domain only, and nine are recommended for one domain only. The
upload template has no cell that says which domain a child belongs to before review (`A7` is filled
in by the data assessment team), so the domain has to be read from the child's other fields. That
is a cross-field rule, which belongs to R4. Until then those fields are checked for type, range and
vocabulary like any other, but an empty one is not reported.

## D-4 — Description rows are found by their labels

The rows under the header are skipped while their column A holds a description row label
(Obligation, Domain, Quality Relevance, Name, Short Name, Unit, Allowed range of values), compared
without regard to case or surrounding spaces. Both the generated template and the hand-maintained
one label every description row this way, so a workbook with more, fewer or no description rows is
read correctly. A row whose label is not one of these is read as a child, and its values are
reported as problems, which shows the assessor exactly where the reading went wrong rather than
silently dropping a row.

## D-5 — The report holds the problems, not a copy of the data

The report is a new file beside the workbook listing every problem with the Excel row of its child,
and a summary of what was checked. Rewriting the whole workbook into a copy costs 20–30 seconds at
90,000 children with every established spreadsheet writer measured (research.md, "Writing the
report"), which alone misses SC-006. Leaving the original's data where it is also keeps one copy
of the data to fix: the assessor works in the original with the report open beside it, and checks
again.

## D-6 — A number in a free-text field is checked as its text

A site name, a comment or an ID that is a number (`12`, `3.5`) is a valid value of a free-text
field. The check reads every cell as the text Excel shows for it, so such a cell is text like any
other and is never reported. It is the mirror of D-1 and changes nothing the assessor typed. A cell
Excel holds as a date reads as a full date and time, so D-2 still reports it.

## D-7 — Text `nan` and infinities are wrong type

The text `nan`, `inf` and `-inf` parses as a number, but none of them is a number an assessor can
have measured. Each is reported once, as wrong type, and no range problem is reported for that
cell.

## D-8 — The speed target is checked by the test suite

SC-006 is a test that generates a workbook of 90,000 children and fails when the check and its
report take longer than 15 seconds. It runs with the rest of the suite, so a change that slows the
check down fails its pull request rather than being found later. Generating the workbook takes
about 30 seconds and is done once per test session.
