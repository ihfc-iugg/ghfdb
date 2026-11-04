"""The IHFC Controlled Vocabularies, read from their permanent identifiers.

A concept scheme is published at its identifier with ``.ttl`` added. Each file is
downloaded through a caching HTTP session, which keeps the file in a cache directory
outside the repository and asks the server whether it changed before using it again.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from rdflib import RDF, Graph, URIRef
from rdflib import Literal as RdfLiteral
from rdflib.collection import Collection
from rdflib.namespace import SKOS
from rdflib.term import Node
from requests import Session
from requests.adapters import HTTPAdapter, Retry
from requests_cache import CachedSession

CACHE_VARIABLE = "GHFDB_VOCABULARY_CACHE"
TIMEOUT = 60
RETRIES = Retry(total=2, backoff_factor=1, status_forcelist=(502, 503, 504))


@dataclass(frozen=True)
class VocabularyBinding:
    """The controlled vocabulary a field takes its values from.

    Attributes:
        scheme: The permanent identifier of the concept scheme.
        collection: The permanent identifier of the ``skos:Collection`` or
            ``skos:OrderedCollection`` that narrows the choice, or None when the
            field takes every concept of the scheme.
        term_form: Whether a value is written as the concept's label or its notation.
    """

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


class MissingSchemeError(LookupError):
    """Raised when a scheme or collection is not defined where it is published."""


def cache_directory() -> Path:
    """Find the directory the downloaded vocabulary files are kept in.

    Returns:
        The directory named by the ``GHFDB_VOCABULARY_CACHE`` environment variable,
        else ``ghfdb/vocabularies`` in the user's cache directory.
    """
    if override := os.environ.get(CACHE_VARIABLE):
        return Path(override)
    base = os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache"
    return Path(base) / "ghfdb" / "vocabularies"


def caching_session() -> Session:
    """Build the session vocabulary files are downloaded with.

    Returns:
        A session that keeps responses in ``cache_directory()``. The server's
        ``ETag``, ``Last-Modified`` and ``Cache-Control`` decide how long a file is
        used without asking, and afterwards the server is asked whether it changed. A
        cached file is used when the server cannot be reached.
    """
    session = CachedSession(
        cache_name=str(cache_directory()),
        backend="filesystem",
        cache_control=True,
        expire_after=0,
        stale_if_error=True,
    )
    session.mount("https://", HTTPAdapter(max_retries=RETRIES))
    return session


class Vocabularies:
    """The vocabulary files a field schema points at."""

    def __init__(self, session: Session | None = None) -> None:
        """Remember how files are downloaded; a file is read when it is needed.

        Args:
            session: The session to download files with. Without one, see
                ``caching_session``.
        """
        self.session = caching_session() if session is None else session
        self.graphs: dict[str, Graph] = {}

    def allowed_values(self, binding: VocabularyBinding) -> tuple[AllowedValue, ...]:
        """The values a field bound to a scheme or collection accepts.

        Args:
            binding: The scheme and optional collection the field names.

        Returns:
            The members of an ordered collection in the collection's order.
            Otherwise the members of the collection, or every concept of the scheme,
            sorted by term ignoring case.

        Raises:
            MissingSchemeError: The file does not define the scheme or collection, or
                a concept has no English preferred label.
            OSError: The file is not cached and cannot be downloaded.
        """
        graph = self.graph(binding.scheme)
        scheme = URIRef(binding.scheme)
        if (scheme, RDF.type, SKOS.ConceptScheme) not in graph:
            raise MissingSchemeError(f"{binding.scheme} is not a concept scheme")
        ordered = False
        concepts: list[Node] | set[Node]
        if binding.collection is None:
            concepts = set(graph.subjects(SKOS.inScheme, scheme))
        else:
            concepts, ordered = self.members(graph, URIRef(binding.collection))
        values = [self.allowed_value(graph, c, binding.term_form) for c in concepts]
        if ordered:
            return tuple(values)
        return tuple(sorted(values, key=lambda value: value.term.casefold()))

    def graph(self, scheme: str) -> Graph:
        """Read the file of one scheme once.

        Args:
            scheme: The scheme's permanent identifier. The file is at the identifier
                with ``.ttl`` added.

        Returns:
            The scheme's graph.

        Raises:
            OSError: The file cannot be downloaded or is not Turtle.
        """
        if scheme not in self.graphs:
            response = self.session.get(f"{scheme}.ttl", timeout=TIMEOUT)
            response.raise_for_status()
            try:
                self.graphs[scheme] = Graph().parse(
                    data=response.content, format="turtle"
                )
            except Exception as error:
                raise OSError(f"{scheme}.ttl is not Turtle: {error}") from error
        return self.graphs[scheme]

    @staticmethod
    def members(
        graph: Graph, collection: URIRef
    ) -> tuple[list[Node] | set[Node], bool]:
        """List the members of a collection.

        Args:
            graph: The graph that defines the collection.
            collection: The collection's identifier.

        Returns:
            The members, and whether they come in the collection's own order, which is
            so for a ``skos:OrderedCollection`` only.

        Raises:
            MissingSchemeError: The graph does not define the collection.
        """
        if (collection, RDF.type, SKOS.OrderedCollection) in graph:
            (head,) = graph.objects(collection, SKOS.memberList)
            return list(Collection(graph, head)), True
        if (collection, RDF.type, SKOS.Collection) in graph:
            return set(graph.objects(collection, SKOS.member)), False
        raise MissingSchemeError(f"{collection} is not a collection")

    @staticmethod
    def allowed_value(graph: Graph, concept: Node, term_form: str) -> AllowedValue:
        """Build the allowed value for one concept.

        Args:
            graph: The graph holding the concept.
            concept: The concept's URI.
            term_form: ``label`` or ``notation``.

        Returns:
            The value, its term written in square brackets.

        Raises:
            MissingSchemeError: If the concept has no English preferred label.
        """
        labels = [
            str(label)
            for label in graph.objects(concept, SKOS.prefLabel)
            if isinstance(label, RdfLiteral) and label.language == "en"
        ]
        if not labels:
            raise MissingSchemeError(f"{concept} has no English preferred label")
        notations = [str(n) for n in graph.objects(concept, SKOS.notation)]
        notation = notations[0] if notations else None
        shown = notation if term_form == "notation" and notation else labels[0]
        return AllowedValue(f"[{shown}]", labels[0], str(concept), notation)
