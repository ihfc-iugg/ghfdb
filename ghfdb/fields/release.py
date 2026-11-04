"""Reading a vocabulary release, and moving a field schema file onto it.

This is the only module that imports rdflib, which is the optional ``vocabularies``
extra. Importing ``ghfdb.fields`` never reaches it.
"""

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass, replace
from functools import cached_property
from pathlib import Path
from typing import Any

from rdflib import RDF, Graph, Literal, URIRef
from rdflib.namespace import DCTERMS, SKOS
from rdflib.term import Node

from ghfdb.fields.schema import AllowedValue, VocabularyBinding, VocabularyRelease

DOI_PREFIX = "https://doi.org/"


class MissingSchemeError(LookupError):
    """Raised when a release holds no scheme or collection of the name asked for."""


class ReleaseFiles:
    """One vocabulary release, read from the directory holding its Turtle files."""

    def __init__(self, directory: Path, version: str) -> None:
        """Remember where the release is; nothing is read until it is needed.

        Args:
            directory: The directory holding the release's ``.ttl`` files.
            version: The release version, such as ``2026.1``. It is never read from
                the files.
        """
        self.directory = directory
        self.version = version

    @cached_property
    def graph(self) -> Graph:
        """All of the release's Turtle files in one graph."""
        graph = Graph()
        for path in sorted(self.directory.glob("*.ttl")):
            graph.parse(path, format="turtle")
        return graph

    @property
    def release(self) -> VocabularyRelease:
        """The version and bare DOI of the release.

        Returns:
            The release, with the DOI read from ``dcterms:isPartOf`` of its schemes.

        Raises:
            ValueError: If the schemes name more than one DOI, or none.
        """
        dois = {
            str(doi).removeprefix(DOI_PREFIX)
            for scheme in self.graph.subjects(RDF.type, SKOS.ConceptScheme)
            for doi in self.graph.objects(scheme, DCTERMS.isPartOf)
        }
        if len(dois) != 1:
            found = ", ".join(sorted(dois)) or "none"
            raise ValueError(f"The schemes must share one DOI; found {found}")
        return VocabularyRelease(self.version, dois.pop())

    def resolve(self, binding: VocabularyBinding) -> VocabularyBinding:
        """Fill in the scheme and collection URIs of a binding given by name.

        Args:
            binding: A binding whose scheme and collection names are set.

        Returns:
            The binding with the URIs the release gives those names.

        Raises:
            MissingSchemeError: If the release has no scheme or collection of the name.
        """
        scheme = self.find(SKOS.ConceptScheme, binding.scheme_name, None)
        collection = None
        if binding.collection_name is not None:
            collection = str(
                self.find(SKOS.Collection, binding.collection_name, str(scheme))
            )
        return replace(binding, scheme=str(scheme), collection=collection)

    def allowed_values(self, binding: VocabularyBinding) -> tuple[AllowedValue, ...]:
        """The values a field bound to a scheme or collection accepts.

        Args:
            binding: The binding, by scheme name and optional collection name.

        Returns:
            The collection's members where the binding names one, otherwise every
            concept of the scheme, sorted by term ignoring case.

        Raises:
            MissingSchemeError: If the release has no scheme or collection of the name.
        """
        resolved = self.resolve(binding)
        scheme = URIRef(resolved.scheme)
        if resolved.collection is None:
            concepts = set(self.graph.subjects(SKOS.inScheme, scheme))
        else:
            concepts = set(self.graph.objects(URIRef(resolved.collection), SKOS.member))
        values = [self.allowed_value(c, resolved.term_form) for c in concepts]
        return tuple(sorted(values, key=lambda value: value.term.casefold()))

    def find(self, kind: URIRef, name: str, within: str | None) -> URIRef:
        """Find the one resource of a kind whose URI ends in a name.

        Args:
            kind: The RDF class, such as ``skos:ConceptScheme``.
            name: The last segment of the URI.
            within: The URI the resource's parent must be, or None for any.

        Returns:
            The resource's URI.

        Raises:
            MissingSchemeError: If the release holds no such resource.
        """
        for subject in self.graph.subjects(RDF.type, kind):
            parent, _, last = str(subject).rpartition("/")
            if last == name and within in (None, parent):
                return URIRef(str(subject))
        raise MissingSchemeError(f"The release has no {kind.split('#')[-1]} '{name}'")

    def allowed_value(self, concept: Node, term_form: str) -> AllowedValue:
        """Build the allowed value for one concept.

        Args:
            concept: The concept's URI.
            term_form: ``label`` or ``notation``.

        Returns:
            The value, its term written in square brackets.

        Raises:
            ValueError: If the concept has no English preferred label.
        """
        labels = [
            str(label)
            for label in self.graph.objects(concept, SKOS.prefLabel)
            if isinstance(label, Literal) and label.language == "en"
        ]
        if not labels:
            raise ValueError(f"{concept} has no English preferred label")
        notations = [str(n) for n in self.graph.objects(concept, SKOS.notation)]
        notation = notations[0] if notations else None
        shown = notation if term_form == "notation" and notation else labels[0]
        return AllowedValue(f"[{shown}]", labels[0], str(concept), notation)


@dataclass(frozen=True)
class FieldChange:
    """What moving to a release does to the allowed values of one field.

    Attributes:
        code: The field's code, such as ``C43``.
        added: Values the release has and the field does not.
        removed: Values the field has and the release does not.
        relabelled: Pairs of the old and new value for a concept whose URI is the
            same and whose term or label differs.
    """

    code: str
    added: tuple[AllowedValue, ...]
    removed: tuple[AllowedValue, ...]
    relabelled: tuple[tuple[AllowedValue, AllowedValue], ...]

    def describe(self) -> str:
        """Write this field's change as a line of the report.

        Returns:
            ``<code>: unchanged``, or the added, removed and relabelled terms.
        """
        parts = []
        if self.added:
            parts.append("added " + ", ".join(value.term for value in self.added))
        if self.removed:
            parts.append("removed " + ", ".join(value.term for value in self.removed))
        if self.relabelled:
            pairs = (f"{old.term} -> {new.term}" for old, new in self.relabelled)
            parts.append("relabelled " + ", ".join(pairs))
        return f"{self.code}: " + ("; ".join(parts) or "unchanged")


class ReleaseMove:
    """Regenerate the allowed values of a field schema file from a release."""

    def __init__(self, schema_path: Path, release: ReleaseFiles) -> None:
        """Pair a field schema file with the release to move it onto.

        Args:
            schema_path: The field schema JSON file to rewrite.
            release: The vocabulary release whose facts the file takes.
        """
        self.schema_path = schema_path
        self.release = release

    def changes(self) -> tuple[FieldChange, ...]:
        """Report what moving onto the release would change, writing nothing.

        Returns:
            One change per vocabulary field, in the order the file lists them.

        Raises:
            MissingSchemeError: If the release lacks a scheme or collection a field
                names.
        """
        data: dict[str, Any] = json.loads(self.schema_path.read_text())
        return tuple(
            self.change(field, values) for field, _, values in self.resolve_all(data)
        )

    def apply(self) -> tuple[FieldChange, ...]:
        """Write the release's facts into the schema file.

        Only the generated facts change: ``vocabulary.scheme``,
        ``vocabulary.collection``, ``allowedValues`` and ``constraints.enum`` of every
        field with a vocabulary, and ``vocabularyRelease``. Every field is resolved
        before anything is written, so a failure leaves the file as it was.

        Returns:
            The same changes ``changes()`` reports.

        Raises:
            MissingSchemeError: If the release lacks a scheme or collection a field
                names. The file is not written.
        """
        data: dict[str, Any] = json.loads(self.schema_path.read_text())
        moves = self.resolve_all(data)
        changes = tuple(self.change(field, values) for field, _, values in moves)
        for field, resolved, values in moves:
            self.write_field(field, resolved, values)
        release = self.release.release
        data["vocabularyRelease"] = {"version": release.version, "doi": release.doi}
        text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        self.schema_path.write_text(text)
        return changes

    def resolve_all(
        self, data: dict[str, Any]
    ) -> list[tuple[dict[str, Any], VocabularyBinding, tuple[AllowedValue, ...]]]:
        """Resolve every vocabulary field against the release.

        Args:
            data: The parsed field schema file.

        Returns:
            For each vocabulary field, the field, its resolved binding and the
            values the release gives it.

        Raises:
            MissingSchemeError: If the release lacks a scheme or collection a field
                names; the message starts with the field's code.
        """
        moves = []
        for field in data["fields"]:
            vocabulary = field.get("vocabulary")
            if vocabulary is None:
                continue
            binding = VocabularyBinding(
                vocabulary["schemeName"],
                vocabulary["collectionName"],
                "",
                None,
                vocabulary["termForm"],
            )
            try:
                resolved = self.release.resolve(binding)
                values = self.release.allowed_values(resolved)
            except MissingSchemeError as error:
                raise MissingSchemeError(f"{field['name']}: {error}") from error
            moves.append((field, resolved, values))
        return moves

    def change(
        self, field: dict[str, Any], values: tuple[AllowedValue, ...]
    ) -> FieldChange:
        """Compare a field's current allowed values with the release's.

        Args:
            field: The parsed field.
            values: The values the release gives the field.

        Returns:
            The values added, removed and relabelled, matched by concept URI.
        """
        old = {item["uri"]: AllowedValue(**item) for item in field["allowedValues"]}
        new = {value.uri: value for value in values}
        return FieldChange(
            field["name"],
            tuple(new[uri] for uri in new if uri not in old),
            tuple(old[uri] for uri in old if uri not in new),
            tuple(
                (old[uri], new[uri])
                for uri in new
                if uri in old
                and (old[uri].term, old[uri].label) != (new[uri].term, new[uri].label)
            ),
        )

    def write_field(
        self,
        field: dict[str, Any],
        resolved: VocabularyBinding,
        values: tuple[AllowedValue, ...],
    ) -> None:
        """Rewrite the generated facts of one vocabulary field in place.

        Args:
            field: The parsed field.
            resolved: The field's binding, resolved against the release.
            values: The values the release gives the field.
        """
        field["vocabulary"]["scheme"] = resolved.scheme
        field["vocabulary"]["collection"] = resolved.collection
        field["allowedValues"] = [
            {key: getattr(value, key) for key in ("term", "uri", "label", "notation")}
            for value in values
        ]
        field.setdefault("constraints", {})["enum"] = [value.term for value in values]


def add_changed_line(text: str, line: str) -> str:
    """Add a bullet under ``### Changed`` of the Unreleased changelog section.

    Args:
        text: The changelog.
        line: The bullet to add, without its dash.

    Returns:
        The changelog with the bullet last under ``### Changed`` of
        ``## [Unreleased]``, the heading created at the end of that section when it
        is absent.
    """
    lines = text.splitlines()
    start = lines.index("## [Unreleased]")
    end = next(
        (i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")),
        len(lines),
    )
    changed = next(
        (i for i in range(start + 1, end) if lines[i] == "### Changed"), None
    )
    if changed is None:
        body = ["", "### Changed", "", f"- {line}"]
        at = end
    else:
        body = [f"- {line}"]
        at = next(
            (i for i in range(changed + 1, end) if lines[i].startswith("### ")), end
        )
    while lines[at - 1] == "":
        at -= 1
    return "\n".join([*lines[:at], *body, *lines[at:]]) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    """Move the field schema onto a release, report it and note it in the changelog.

    Args:
        argv: The command line without the program name; ``sys.argv`` when None.

    Returns:
        0 on success; 1 when the release lacks a scheme or collection a field
        names, in which case neither file is changed.
    """
    parser = argparse.ArgumentParser(
        prog="python -m ghfdb.fields.release", description=__doc__
    )
    parser.add_argument("version", help="the release version, such as 2026.1")
    parser.add_argument("directory", type=Path, help="the release's Turtle files")
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path(__file__).with_name("schema.json"),
        help="the field schema file; the packaged one by default",
    )
    parser.add_argument(
        "--changelog",
        type=Path,
        default=Path("CHANGELOG.md"),
        help="the changelog; CHANGELOG.md in the current directory by default",
    )
    args = parser.parse_args(argv)
    files = ReleaseFiles(args.directory, args.version)
    old = json.loads(args.schema.read_text())["vocabularyRelease"]
    new = files.release
    line = (
        f"Vocabulary release moved from {old['version']} (DOI {old['doi']}) "
        f"to {new.version} (DOI {new.doi})."
    )
    changelog = add_changed_line(args.changelog.read_text(), line)
    try:
        changes = ReleaseMove(args.schema, files).apply()
    except MissingSchemeError as error:
        print(error, file=sys.stderr)
        return 1
    for change in changes:
        print(change.describe())
    args.changelog.write_text(changelog)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
