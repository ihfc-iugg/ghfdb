"""Every criterion of the quality scheme that is a table, and the terms they name.

The criteria are declared in ``probe`` and ``borehole``. This module lists them by the
identifier the worked examples use, and resolves the concepts a scoring names to the
terms the fields accept.
"""

from collections.abc import Iterable

from frictionless import Schema

from ghfdb.fields import MissingSchemeError, Vocabularies
from ghfdb.fields.cells import concept_terms
from ghfdb.qc.borehole import BoreholeRules
from ghfdb.qc.penalties import Criterion, Table
from ghfdb.qc.probe import ProbeRules

CRITERIA: dict[str, Criterion[Table]] = {
    criterion.identifier: criterion
    for rules in (ProbeRules, BoreholeRules)
    for criterion in rules.declared()
}


def term_uris(
    schema: Schema,
    concepts: Iterable[tuple[str, str]],
    vocabularies: Vocabularies | None = None,
) -> dict[str, dict[str, str]]:
    """Resolve the concepts a scoring names to the terms their fields accept.

    Args:
        schema: The fields, which say where each takes its allowed values from.
        concepts: The field code and concept URI of every concept to resolve.
        vocabularies: Where the allowed values come from. Without it, the vocabularies
            in the user's cache, downloaded when missing.

    Returns:
        For each field named, the concept URI of every term it accepts that has one, by
        term. A term the scoring does not name is included, so a method the scheme does
        not know is a concept in no group and not an empty value.

    Raises:
        MissingSchemeError: A concept is not an allowed value of its field, or the
            field is not in the schema. The message names the field and the concept.
        OSError: The vocabularies are not cached and cannot be downloaded.
    """
    files = Vocabularies() if vocabularies is None else vocabularies
    pairs = tuple(concepts)
    allowed = {
        code: concept_terms(schema, code, files)
        for code in dict.fromkeys(code for code, _ in pairs)
    }
    for code, uri in pairs:
        if uri not in allowed[code]:
            raise MissingSchemeError(f"{code}: {uri} is not an allowed value")
    return {
        code: {term: uri for uri, term in terms.items()}
        for code, terms in allowed.items()
    }
