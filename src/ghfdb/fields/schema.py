"""The field schema: the facts the upload template records about each field."""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class VocabularyRelease:
    """The release of the IHFC Controlled Vocabularies a schema was built from.

    Attributes:
        version: The release version, such as ``2026.1``.
        doi: The bare DOI of the release, without a resolver prefix.
    """

    version: str
    doi: str


@dataclass(frozen=True)
class VocabularyBinding:
    """The controlled vocabulary a field takes its values from.

    Attributes:
        scheme_name: The last segment of the concept scheme URI.
        collection_name: The last segment of the collection URI, or None when the
            field takes every concept of the scheme.
        scheme: The full URI of the concept scheme.
        collection: The full URI of the collection, or None.
        term_form: Whether a value is written as the concept's label or its notation.
    """

    scheme_name: str
    collection_name: str | None
    scheme: str
    collection: str | None
    term_form: Literal["label", "notation"]


@dataclass(frozen=True)
class AllowedValue:
    """One value a field accepts.

    Attributes:
        term: The value as written in the template, in square brackets.
        label: The English preferred label of the concept.
        uri: The concept URI, or None for a value that belongs to no vocabulary.
        notation: The concept's notation, or None when it has none.
    """

    term: str
    label: str
    uri: str | None
    notation: str | None
