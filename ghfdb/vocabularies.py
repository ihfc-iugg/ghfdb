"""The controlled vocabularies, read from where they are published.

``concepts`` names a concept of a field's vocabulary in code, from the field schema alone.
The rest of the module reads the vocabularies themselves.

The IHFC Controlled Vocabularies publish a concept scheme at its identifier with
``.ttl`` added. A field whose scheme is not published there names the file to download
and its RDF format. Each file is downloaded through a caching HTTP session, which keeps
the file in a cache directory outside the repository and asks the server whether it
changed before using it again.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import timedelta
from importlib import resources
from pathlib import Path
from typing import Self

from platformdirs import user_cache_dir
from rdflib import RDF, Graph, Namespace, URIRef
from rdflib import Literal as RdfLiteral
from rdflib.collection import Collection
from rdflib.namespace import DCTERMS, SKOS
from rdflib.term import Node
from requests import Session
from requests.adapters import HTTPAdapter, Retry
from requests_cache import CachedSession

TURTLE = "text/turtle"
FORMAT_NAMES = {TURTLE: "Turtle", "application/rdf+xml": "RDF/XML"}
TIMEOUT = 60
RETRIES = Retry(total=2, backoff_factor=1, status_forcelist=(502, 503, 504))


@dataclass(frozen=True)
class AllowedValue:
    """One value a field accepts.

    Attributes:
        term: The value as written in the template: in square brackets, except the
            local name of a concept's URI, which the template writes bare.
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


def local_name(uri: str) -> str:
    """Name a concept within its vocabulary.

    Args:
        uri: The concept URI.

    Returns:
        The last path segment of the URI.
    """
    return uri.rsplit("/", 1)[-1]


def caching_session(directory: Path | None = None) -> Session:
    """Build the session vocabulary files are downloaded with.

    Args:
        directory: Where to keep the downloaded files. Without it,
            ``vocabularies`` in the user's cache directory for ghfdb.

    Returns:
        A session that keeps responses in the directory. The server's ``ETag``,
        ``Last-Modified`` and ``Cache-Control`` decide how long a file is used without
        asking, and afterwards the server is asked whether it changed. A file sent
        with none of these headers cannot be checked, so it is used for a day and
        downloaded again after that. A cached file is used when the server cannot
        be reached.
    """
    if directory is None:
        directory = Path(user_cache_dir("ghfdb")) / "vocabularies"
    session = CachedSession(
        cache_name=str(directory),
        backend="filesystem",
        cache_control=True,
        expire_after=timedelta(days=1),
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

    def allowed_values(
        self, vocabulary: Mapping[str, str | None]
    ) -> tuple[AllowedValue, ...]:
        """The values a field that draws on a controlled vocabulary accepts.

        Args:
            vocabulary: The field's ``vocabulary`` object: the permanent identifier
                of its ``scheme``, of the ``collection`` that narrows the choice (or
                None when the field takes every concept of the scheme), and the
                ``termForm``, ``label``, ``notation`` or ``localName``, in which a
                value is written. A scheme not published at its identifier also has
                the ``download`` address of its file and its ``downloadFormat``, a
                media type of ``FORMAT_NAMES``.

        Returns:
            The members of an ordered collection in the collection's order.
            Otherwise the members of the collection, or every concept of the scheme,
            sorted by term ignoring case.

        Raises:
            MissingSchemeError: The file does not define the scheme or collection, or
                a concept has no English preferred label.
            OSError: The file is not cached and cannot be downloaded.
        """
        scheme, collection = vocabulary["scheme"], vocabulary["collection"]
        assert scheme is not None
        graph = self.graph(
            scheme, vocabulary.get("download"), vocabulary.get("downloadFormat")
        )
        if (URIRef(scheme), RDF.type, SKOS.ConceptScheme) not in graph:
            raise MissingSchemeError(f"{scheme} is not a concept scheme")
        ordered = False
        concepts: list[Node] | set[Node]
        if collection is None:
            concepts = set(graph.subjects(SKOS.inScheme, URIRef(scheme)))
        else:
            concepts, ordered = self.members(graph, URIRef(collection))
        term_form = vocabulary["termForm"]
        values = [self.allowed_value(graph, c, term_form) for c in concepts]
        if ordered:
            return tuple(values)
        return tuple(sorted(values, key=lambda value: value.term.casefold()))

    def graph(
        self,
        scheme: str,
        download: str | None = None,
        media_type: str | None = None,
    ) -> Graph:
        """Read the file of one scheme once.

        Args:
            scheme: The scheme's permanent identifier.
            download: The address of the scheme's file. Without it, the identifier
                with ``.ttl`` added.
            media_type: The RDF format of the file, a key of ``FORMAT_NAMES``.
                Without it, Turtle.

        Returns:
            The scheme's graph.

        Raises:
            OSError: The file cannot be downloaded or is not in its format.
        """
        if scheme not in self.graphs:
            address = download or f"{scheme}.ttl"
            response = self.session.get(address, timeout=TIMEOUT)
            response.raise_for_status()
            media_type = media_type or TURTLE
            try:
                self.graphs[scheme] = Graph().parse(
                    data=response.content, format=media_type
                )
            except Exception as error:
                name = FORMAT_NAMES[media_type]
                raise OSError(f"{address} is not {name}: {error}") from error
        return self.graphs[scheme]

    def releases(self) -> list[str]:
        """List the releases of the vocabularies this instance has read.

        Returns:
            The identifier of each release that a concept scheme read so far is part
            of (``dcterms:isPartOf``), sorted and without repeats.
        """
        found: set[str] = set()
        for graph in self.graphs.values():
            for scheme in graph.subjects(RDF.type, SKOS.ConceptScheme):
                found.update(str(o) for o in graph.objects(scheme, DCTERMS.isPartOf))
        return sorted(found)

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
            so for a ``skos:OrderedCollection`` only. The members of a
            ``skos:Collection`` that is itself a member are members of the collection.

        Raises:
            MissingSchemeError: The graph does not define the collection.
        """
        if (collection, RDF.type, SKOS.OrderedCollection) in graph:
            (head,) = graph.objects(collection, SKOS.memberList)
            return list(Collection(graph, head)), True
        if (collection, RDF.type, SKOS.Collection) in graph:
            members: set[Node] = set()
            for member in graph.objects(collection, SKOS.member):
                if (member, RDF.type, SKOS.Collection) in graph:
                    members.update(Vocabularies.members(graph, URIRef(str(member)))[0])
                else:
                    members.add(member)
            return members, False
        raise MissingSchemeError(f"{collection} is not a collection")

    @staticmethod
    def allowed_value(
        graph: Graph, concept: Node, term_form: str | None
    ) -> AllowedValue:
        """Build the allowed value for one concept.

        Args:
            graph: The graph holding the concept.
            concept: The concept's URI.
            term_form: ``label``, ``notation`` or ``localName``.

        Returns:
            The value, its term written in square brackets, except a local name.

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
        found = graph.value(concept, SKOS.notation)
        notation = None if found is None else str(found)
        if term_form == "localName":
            term = local_name(str(concept))
        else:
            shown = notation if term_form == "notation" and notation else labels[0]
            term = f"[{shown}]"
        return AllowedValue(term, labels[0], str(concept), notation)


class Concepts:
    """The concepts of the vocabularies, named in code.

    A field that draws on a vocabulary is a namespace of its concept scheme, so a
    concept is ``concepts.tc_method.pointSource``, or, when its local name is not a
    Python name, ``concepts.tc_source["insitu-probe"]``. Each is the concept's ``URIRef``.
    The namespaces are built from the packaged field schema, never from the web.

    Args:
        namespaces: The namespace of the scheme of each field that has a vocabulary, by
            the field's published column name.
    """

    def __init__(self, namespaces: Mapping[str, Namespace]) -> None:
        self.namespaces = namespaces

    @classmethod
    def packaged(cls) -> Self:
        """Read the schemes of the fields from the packaged field schema.

        Returns:
            The concepts of every field of the schema that has a vocabulary.
        """
        schema = resources.files("ghfdb").joinpath("fields", "schema.json")
        fields = json.loads(schema.read_text("utf-8"))["fields"]
        return cls(
            {
                field["columnName"]: Namespace(f"{field['vocabulary']['scheme']}/")
                for field in fields
                if field["vocabulary"]
            }
        )

    def __getitem__(self, column_name: str) -> Namespace:
        """Find the namespace of a field's concept scheme.

        Args:
            column_name: The field's published column name.

        Returns:
            The scheme's identifier with a slash added.

        Raises:
            AttributeError: No field has the column name, or the field has no
                vocabulary.
        """
        try:
            return self.namespaces[column_name]
        except KeyError:
            raise AttributeError(
                f"{column_name} is not the column name of a field with a vocabulary"
            ) from None

    def __getattr__(self, column_name: str) -> Namespace:
        """Find the namespace of a field's concept scheme, as ``concepts[name]`` does."""
        if column_name == "namespaces" or column_name.startswith("__"):
            raise AttributeError(column_name)
        return self[column_name]


concepts = Concepts.packaged()
