# Upload template

The package generates the upload template, the workbook a contributor fills in, from the
field schema. It has three sheets: `readme`, `data list` and `controlled vocabulary`. The
`data list` sheet has a header row of field codes and a description row for each of the
obligation, domain, quality relevance, name, published column name, unit and allowed range of
values. Fields with a fixed list of allowed values get a choice list. Generating the
template reads the vocabulary release from the cache, which downloads it on first use (see
[Field definitions](field-definitions.md)).

## Generate the template

1. Import `UploadTemplate` and create it. Without arguments it uses the field schema shipped
   with the package.

   ```python
   from ghfdb.template import UploadTemplate

   template = UploadTemplate()
   ```

2. Write it to a path.

   ```python
   from pathlib import Path

   path = Path("upload-template.xlsx")
   template.write(path)
   ```

To build the workbook without saving it, call `template.workbook()`, which returns an
openpyxl `Workbook`.

## Choose where the template goes

1. Pass any path that ends in `.xlsx`. The directory must exist.

   ```python
   template.write(Path("out") / "ghfdb-upload-template.xlsx")
   ```

2. To generate from a different set of fields, load their schema file with
   {py:class}`~ghfdb.fields.FieldSchema` and pass it when you create the template.

   ```python
   from ghfdb.fields import FieldSchema

   schema = FieldSchema.load(Path("my-field-schema.json"))
   UploadTemplate(schema).write(Path("my-upload-template.xlsx"))
   ```

## Replace an existing file

`write` refuses a path that already holds a file. It raises `FileExistsError` naming the
path, and leaves the file as it was.

1. To overwrite the file, pass `replace=True`.

   ```python
   template.write(path, replace=True)
   ```

## Find the version and vocabulary release a template came from

1. Open the template and read its `readme` sheet. It states the package version that
   generated the workbook, the version of the IHFC Controlled Vocabularies release the
   choice lists come from, and a link to the field reference.

2. Or read the same facts from the template before writing it. `version` is the package
   version, and the schema names the release.

   ```python
   template.version
   template.schema.release.version
   ```

## Why the file is never replaced by default

A contributor may have filled in a template already. Overwriting it silently would lose their
work, so replacing is something you ask for.

## Why two templates generated from the same schema differ in bytes

openpyxl records the time a workbook is saved, so the bytes of two files differ. Their
content does not: the same sheets, the same cell values and the same choice lists.
