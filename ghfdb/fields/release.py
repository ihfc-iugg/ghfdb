"""The IHFC Controlled Vocabularies release a field schema names, and its files.

A release is downloaded once from its GitHub release into a cache directory outside the
repository, keyed by version, and read from there afterwards.
"""

import os
import shutil
import tempfile
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Self
from urllib.request import urlopen

from rdflib import RDF, Graph, URIRef
from rdflib import Literal as RdfLiteral
from rdflib.collection import Collection
from rdflib.namespace import SKOS
from rdflib.term import Node

CACHE_VARIABLE = "GHFDB_VOCABULARY_CACHE"
ARCHIVE = "vocabularies-full.zip"
TIMEOUT = 60


@dataclass(frozen=True)
class VocabularyRelease:
    """The release of the IHFC Controlled Vocabularies a schema takes its terms from.

    Attributes:
        version: The release version, such as ``2026.1``.
        doi: The bare DOI of the release, without a resolver prefix.
        repository: The address of the repository the release is published in.
    """

    version: str
    doi: str
    repository: str

    @property
    def archive_url(self) -> str:
        """Where the release's vocabulary files are downloaded from."""
        return f"{self.repository}/releases/download/v{self.version}/{ARCHIVE}"


@dataclass(frozen=True)
class VocabularyBinding:
    """The controlled vocabulary a field takes its values from.

    Attributes:
        scheme_name: The last segment of the concept scheme URI, which is also the
            name of the release file holding the scheme.
        collection_name: The last segment of the collection URI, or None when the
            field takes every concept of the scheme.
        term_form: Whether a value is written as the concept's label or its notation.
    """

    scheme_name: str
    collection_name: str | None
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
    """Raised when a release holds no scheme or collection of the name asked for."""


def cache_directory() -> Path:
    """Find the directory the downloaded releases are kept in.

    Returns:
        The directory named by the ``GHFDB_VOCABULARY_CACHE`` environment variable,
        else ``ghfdb/vocabularies`` in the user's cache directory.
    """
    if override := os.environ.get(CACHE_VARIABLE):
        return Path(override)
    base = os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache"
    return Path(base) / "ghfdb" / "vocabularies"


def download(release: VocabularyRelease, directory: Path) -> None:
    """Download a release's vocabulary files into a directory.

    The files are unpacked beside the directory and moved into place at the end, so
    a download that fails leaves nothing that reads as a release.

    Args:
        release: The release to download.
        directory: Where to put its ``.ttl`` files.

    Raises:
        OSError: The release cannot be downloaded, or holds no Turtle files.
    """
    directory.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=directory.parent) as scratch:
        archive = Path(scratch) / ARCHIVE
        with urlopen(release.archive_url, timeout=TIMEOUT) as response:
            archive.write_bytes(response.read())
        unpacked = Path(scratch) / "release"
        unpacked.mkdir()
        try:
            with zipfile.ZipFile(archive) as zipped:
                for name in zipped.namelist():
                    if name.endswith(".ttl"):
                        (unpacked / Path(name).name).write_bytes(zipped.read(name))
        except zipfile.BadZipFile as error:
            raise OSError(f"{release.archive_url} is not a zip archive") from error
        if not any(unpacked.iterdir()):
            raise OSError(f"{release.archive_url} holds no Turtle files")
        shutil.move(unpacked, directory)


class ReleaseFiles:
    """One vocabulary release, read from the directory holding its Turtle files."""

    def __init__(self, directory: Path) -> None:
        """Remember where the release is; a file is read when its scheme is asked for.

        Args:
            directory: The directory holding the release's ``.ttl`` files, one per
                concept scheme, named for the scheme.
        """
        self.directory = directory
        self.graphs: dict[str, Graph] = {}

    @classmethod
    def fetch(cls, release: VocabularyRelease, cache: Path | None = None) -> Self:
        """Open a release, downloading it first when it is not in the cache.

        Args:
            release: The release to open.
            cache: The directory releases are kept in; see ``cache_directory``.

        Returns:
            The release's files.

        Raises:
            OSError: The release is not cached and cannot be downloaded.
        """
        directory = (cache or cache_directory()) / release.version
        if not directory.is_dir():
            download(release, directory)
        return cls(directory)

    def allowed_values(self, binding: VocabularyBinding) -> tuple[AllowedValue, ...]:
        """The values a field bound to a scheme or collection accepts.

        Args:
            binding: The binding, by scheme name and optional collection name.

        Returns:
            The members of an ordered collection in the collection's order. Otherwise
            the members of the collection, or every concept of the scheme, sorted by
            term ignoring case.

        Raises:
            MissingSchemeError: If the release has no scheme or collection of the name,
                or a concept has no English preferred label.
        """
        graph = self.graph(binding.scheme_name)
        scheme = self.find(graph, SKOS.ConceptScheme, binding.scheme_name, None)
        concepts: Iterable[Node]
        ordered = False
        if binding.collection_name is None:
            concepts = set(graph.subjects(SKOS.inScheme, scheme))
        else:
            concepts, ordered = self.members(graph, binding.collection_name, scheme)
        values = [self.allowed_value(graph, c, binding.term_form) for c in concepts]
        if ordered:
            return tuple(values)
        return tuple(sorted(values, key=lambda value: value.term.casefold()))

    def graph(self, scheme_name: str) -> Graph:
        """Read the file of one scheme, once.

        Args:
            scheme_name: The scheme's name, which is its file's name without ``.ttl``.

        Returns:
            The scheme's graph.

        Raises:
            MissingSchemeError: If the release has no file for the scheme.
        """
        if scheme_name not in self.graphs:
            path = self.directory / f"{scheme_name}.ttl"
            if not path.is_file():
                raise MissingSchemeError(
                    f"The release has no ConceptScheme '{scheme_name}'"
                )
            self.graphs[scheme_name] = Graph().parse(path, format="turtle")
        return self.graphs[scheme_name]

    def members(
        self, graph: Graph, name: str, scheme: URIRef
    ) -> tuple[Iterable[Node], bool]:
        """List the members of a collection of a scheme.

        Args:
            graph: The scheme's graph.
            name: The last segment of the collection's URI.
            scheme: The scheme the collection belongs to.

        Returns:
            The members, and whether they are in the order the release gives, which
            is so for a ``skos:OrderedCollection`` only.

        Raises:
            MissingSchemeError: If the scheme has no collection of the name.
        """
        try:
            collection = self.find(graph, SKOS.Collection, name, scheme)
        except MissingSchemeError:
            ordered = self.find(graph, SKOS.OrderedCollection, name, scheme)
            (head,) = graph.objects(ordered, SKOS.memberList)
            return list(Collection(graph, head)), True
        return set(graph.objects(collection, SKOS.member)), False

    @staticmethod
    def find(graph: Graph, kind: URIRef, name: str, within: URIRef | None) -> URIRef:
        """Find the one resource of a kind whose URI ends in a name.

        Args:
            graph: The graph to search.
            kind: The RDF class, such as ``skos:ConceptScheme``.
            name: The last segment of the URI.
            within: The URI the resource's parent must be, or None for any.

        Returns:
            The resource's URI.

        Raises:
            MissingSchemeError: If the graph holds no such resource.
        """
        for subject in graph.subjects(RDF.type, kind):
            parent, _, last = str(subject).rpartition("/")
            if last == name and within in (None, URIRef(parent)):
                return URIRef(str(subject))
        raise MissingSchemeError(f"The release has no {kind.split('#')[-1]} '{name}'")

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
