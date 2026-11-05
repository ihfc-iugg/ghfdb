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
