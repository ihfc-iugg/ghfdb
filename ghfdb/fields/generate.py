"""Write ``ghfdb/fields/names.py`` from the packaged field schema.

Run ``python -m ghfdb.fields.generate`` after the schema changes.
"""

import json
from importlib import resources
from pathlib import Path
from typing import Any


class FieldNames:
    """The source of the module that names every field by its column name."""

    HEADER = '''"""The column name of every field of the upload template.

This file is generated from ``schema.json`` by ``python -m ghfdb.fields.generate``.
Do not edit it by hand: change the schema and generate it again.
"""

from enum import StrEnum


class Field(StrEnum):
    """A field of the upload template, named by its published column name.

    The value of a member is the field's code, which is how a dataset is keyed.
    """

'''

    @classmethod
    def render(cls, fields: list[dict[str, Any]]) -> str:
        """Write the source of the names module.

        Args:
            fields: The fields of the schema file, in schema order.

        Returns:
            One member for each field, named by its column name, valued by its code.
        """
        members = "".join(
            f'    {field["columnName"]} = "{field["name"]}"\n' for field in fields
        )
        return cls.HEADER + members

    @classmethod
    def write(cls) -> Path:
        """Generate the names module from the packaged schema and write it.

        Returns:
            The path of the file written.
        """
        schema = resources.files("ghfdb.fields").joinpath("schema.json")
        fields = json.loads(schema.read_text("utf-8"))["fields"]
        path = Path(__file__).with_name("names.py")
        path.write_text(cls.render(fields), encoding="utf-8")
        return path


if __name__ == "__main__":
    FieldNames.write()
