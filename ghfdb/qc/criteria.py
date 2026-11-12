"""Every criterion of the quality scheme that is a table, and the terms they name.

The criteria are declared in ``probe`` and ``borehole``. This module lists them by the
identifier the worked examples use, and resolves the concepts a scoring names to the
terms the fields accept, by their local names.
"""

from collections.abc import Iterable

from frictionless import Schema

from ghfdb.fields.cells import terms_by_name
from ghfdb.qc.borehole import BoreholeRules
from ghfdb.qc.penalties import Criterion, Table
from ghfdb.qc.probe import ProbeRules
from ghfdb.vocabularies import MissingSchemeError, Vocabularies

CRITERIA: dict[str, Criterion[Table]] = {
    criterion.identifier: criterion
    for rules in (ProbeRules, BoreholeRules)
    for criterion in rules.declared()
}


def term_names(
    schema: Schema,
    concepts: Iterable[tuple[str, str]],
    vocabularies: Vocabularies | None = None,
) -> dict[str, dict[str, str]]:
    """Resolve the concepts a scoring names to the terms their fields accept.

    Args:
        schema: The fields, which say where each takes its allowed values from.
        concepts: The field code and local name of every concept to resolve.
        vocabularies: Where the allowed values come from. Without it, the vocabularies
            in the user's cache, downloaded when missing.

    Returns:
        For each field named, the local name of every term it accepts that has one,
        by term. A term the scoring does not name is included, so a method the
        scheme does not know is a concept in no group and not an empty value.

    Raises:
        MissingSchemeError: A concept is not an allowed value of its field, the field
            is not in the schema, or two of its allowed values share a local name.
            The message names the field and the name.
        OSError: The vocabularies are not cached and cannot be downloaded.
    """
    files = Vocabularies() if vocabularies is None else vocabularies
    pairs = tuple(concepts)
    allowed = {
        code: terms_by_name(schema, code, files)
        for code in dict.fromkeys(code for code, _ in pairs)
    }
    for code, name in pairs:
        if name not in allowed[code]:
            raise MissingSchemeError(f"{code}: {name} is not an allowed value")
    return {
        code: {term: name for name, term in terms.items()}
        for code, terms in allowed.items()
    }
