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

## D-5 — The report copy holds values, not formulas

The workbook is read with the value Excel last saved for each formula, and the report copy is
written from that same reading, so a formula reaches the report copy as its value. The report
shows what was checked. The original keeps its formulas.

## D-6 — A number in a free-text field is checked as its text

A site name, a comment or an ID that is a number (`12`, `3.5`) is a valid value of a free-text
field. Excel stores it as a number, and Frictionless rejects a number in a text field, so the check
gives such a cell as its text. It is the mirror of D-1 and changes nothing the assessor typed. A
cell Excel holds as a date is not given as text, so D-2 still reports it.

## D-7 — Text `nan` and infinities are wrong type

Python reads the text `nan`, `inf` and `-inf` as numbers, so Frictionless accepts them in a number
field and then reports range errors, two of them for `nan`. None of them is a number an assessor
can have measured, so each is reported once, as wrong type, and the range errors on that cell are
dropped.

## Design review notes carried into the build

Recorded, not acted on in the plan: report sheets named `problems` and `check` would be renamed
by openpyxl if the workbook already has sheets of those names (the reference page says so); the
two earlier column names sit in a description row of the hand-maintained template, so scenario
1.15 is tested by editing the header; reading an untrusted workbook needs no change for XML
entity attacks, because the bundled expat refuses external entities and limits amplification.
