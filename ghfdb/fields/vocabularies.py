"""The IHFC Controlled Vocabularies, read from their permanent identifiers.

A concept scheme is published at its identifier with ``.ttl`` added. Each file is
downloaded into a cache directory outside the repository the first time it is needed,
and downloaded again when the cached copy is older than a week.
"""

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.error import HTTPError
from urllib.request import urlopen

from rdflib import RDF, Graph, URIRef
from rdflib import Literal as RdfLiteral
from rdflib.collection import Collection
from rdflib.namespace import SKOS
from rdflib.term import Node

CACHE_VARIABLE = "GHFDB_VOCABULARY_CACHE"
MAX_AGE_SECONDS = 7 * 24 * 60 * 60
TIMEOUT = 60
ATTEMPTS = 3


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


class Vocabularies:
    """The vocabulary files a field schema points at, cached on disk."""

    def __init__(self, cache: Path | None = None) -> None:
        """Remember where the files are kept; a file is read when it is needed.

        Args:
            cache: The directory holding one ``<scheme name>.ttl`` file per scheme.
                Without one, see ``cache_directory``.
        """
        self.directory = cache or cache_directory()
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
        """Read the file of one scheme, downloading it when it is missing or old.

        Args:
            scheme: The scheme's permanent identifier. The file is at the identifier
                with ``.ttl`` added and is cached under the identifier's last segment.

        Returns:
            The scheme's graph.

        Raises:
            OSError: The file is not cached and cannot be downloaded.
        """
        if scheme not in self.graphs:
            path = self.directory / f"{scheme.rsplit('/', 1)[-1]}.ttl"
            if not path.is_file():
                self.download(scheme, path)
            elif time.time() - path.stat().st_mtime > MAX_AGE_SECONDS:
                try:
                    self.download(scheme, path)
                except OSError:
                    pass  # keep working offline on the copy we have
            self.graphs[scheme] = Graph().parse(path, format="turtle")
        return self.graphs[scheme]

    @staticmethod
    def fetch(address: str) -> bytes:
        """Read a file from the web, trying again when the server fails.

        Args:
            address: The address to read.

        Returns:
            The file's content.

        Raises:
            OSError: The file cannot be read after ``ATTEMPTS`` tries, or the
                server answered with anything but a server error.
        """
        for attempt in range(1, ATTEMPTS + 1):
            try:
                with urlopen(address, timeout=TIMEOUT) as response:
                    content: bytes = response.read()
                return content
            except HTTPError as error:
                if error.code < 500 or attempt == ATTEMPTS:
                    raise
                time.sleep(attempt)
        raise AssertionError("unreachable")  # pragma: no cover

    @staticmethod
    def download(scheme: str, path: Path) -> None:
        """Download a scheme's Turtle file into the cache.

        The file is written only once it parses, so a failed download leaves the
        cache as it was.

        Args:
            scheme: The scheme's permanent identifier.
            path: Where to put the file.

        Raises:
            OSError: The file cannot be downloaded or is not Turtle.
        """
        content = Vocabularies.fetch(f"{scheme}.ttl")
        try:
            Graph().parse(data=content, format="turtle")
        except Exception as error:
            raise OSError(f"{scheme}.ttl is not Turtle: {error}") from error
        path.parent.mkdir(parents=True, exist_ok=True)
        partial = path.with_suffix(".partial")
        partial.write_bytes(content)
        partial.replace(path)

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
