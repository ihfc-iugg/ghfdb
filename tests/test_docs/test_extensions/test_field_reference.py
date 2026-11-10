import json
import re
from pathlib import Path

import pytest
from extensions.field_reference import FieldReference, copy_schema
from frictionless import Field, Schema

from ghfdb.fields import AllowedValue, Vocabularies, allowed_values
from ghfdb.template import VOCABULARIES

GITHUB_DECISIONS = "https://github.com/ihfc-iugg/ghfdb/blob/main/specs/001-field-reference/decisions.md"
ALWAYS_SHOWN = (
    "code",
    "columnName",
    "name",
    "meaning",
    "type",
    "unit",
    "obligation",
    "domain",
    "qualityRelevance",
)


@pytest.fixture(scope="module")
def reference(schema: Schema, published_vocabularies: Vocabularies) -> FieldReference:
    return FieldReference(schema, published_vocabularies)


def column_name(field: Field) -> str:
    return str(field.custom["columnName"])


def sources_of(field: Field) -> dict[str, str]:
    sources: dict[str, str] = field.custom["sources"]
    return sources


def entries_of(reference: FieldReference, field: Field) -> str:
    """Render the entries of the group a field belongs to."""
    return reference.entries(field.custom["group"])


def section_of(markdown: str, field: Field) -> str:
    """Return the text of one field's entry on a group's page."""
    marker = f"(field-{field.name.lower()})=\n"
    start = markdown.index(marker)
    following = markdown.find("\n\n(field-", start + len(marker))
    return markdown[start:] if following == -1 else markdown[start:following]


class TestFieldReferenceEntries:
    @pytest.mark.parametrize("group", ["parent", "child", "assessment"])
    def test_each_field_has_one_entry_on_its_group_page_in_code_order(
        self, schema: Schema, reference: FieldReference, group: str
    ) -> None:
        markdown = reference.entries(group)

        codes = re.findall(r"^\(field-([a-z]\d+)\)=$", markdown, re.MULTILINE)
        expected = [f.name.lower() for f in schema.fields if f.custom["group"] == group]
        assert codes == expected

    def test_the_three_groups_hold_all_seventy_four_fields(
        self, schema: Schema, reference: FieldReference
    ) -> None:
        total = sum(
            len(re.findall(r"^\(field-[a-z]\d+\)=$", reference.entries(g), re.M))
            for g in ("parent", "child", "assessment")
        )

        assert total == len(schema.fields) == 74

    def test_each_entry_has_a_target_for_its_code_and_for_its_column_name(
        self, schema: Schema, reference: FieldReference
    ) -> None:
        for field in schema.fields:
            section = section_of(entries_of(reference, field), field)

            assert f"(field-{field.name.lower()})=\n" in section, field.name
            assert f"(field-{column_name(field).lower()})=\n" in section, field.name

    def test_no_two_fields_share_a_target(self, schema: Schema) -> None:
        targets = [f.name.lower() for f in schema.fields]
        targets += [column_name(f).lower() for f in schema.fields]

        assert len(set(targets)) == len(targets)

    def test_the_heading_sits_one_level_below_the_page_title(
        self, schema: Schema, reference: FieldReference
    ) -> None:
        for field in schema.fields:
            section = section_of(entries_of(reference, field), field)

            headings = re.findall(r"^(#+) ", section, re.MULTILINE)
            assert headings == ["##"], field.name
            assert field.name in section.split("\n## ", 1)[1].split("\n", 1)[0]

    def test_every_entry_names_its_column_name_and_links_each_decision_it_cites(
        self, schema: Schema, reference: FieldReference
    ) -> None:
        for field in schema.fields:
            section = section_of(entries_of(reference, field), field)

            assert f"`{column_name(field)}`" in section, field.name
            for key in ALWAYS_SHOWN:
                source = sources_of(field)[key]
                if source.startswith("decision:"):
                    label = source.removeprefix("decision:")
                    assert f"[Decision {label}]({GITHUB_DECISIONS})" in section

    def test_a_missing_fact_shows_an_em_dash(
        self, schema: Schema, reference: FieldReference
    ) -> None:
        field = schema.get_field("C25")
        assert field.custom["unit"] is None

        section = section_of(entries_of(reference, field), field)

        assert "| Unit | — |" in section

    def test_vocabulary_sources_link_the_published_vocabularies(
        self, schema: Schema, reference: FieldReference
    ) -> None:
        field = schema.get_field("C43")

        section = section_of(entries_of(reference, field), field)

        assert f"[IHFC Controlled Vocabularies]({VOCABULARIES})" in section

    def test_the_decision_source_links_to_the_recorded_decisions(
        self, schema: Schema, reference: FieldReference
    ) -> None:
        field = schema.get_field("P1")
        decision = sources_of(field)["type"]
        assert decision.startswith("decision:")

        section = section_of(entries_of(reference, field), field)

        label = decision.removeprefix("decision:")
        assert f"[Decision {label}]({GITHUB_DECISIONS})" in section


class TestFactOrder:
    def test_every_entry_opens_with_code_column_name_and_name_in_that_order(
        self, reference: FieldReference, schema: Schema
    ) -> None:
        for field in schema.fields:
            section = section_of(entries_of(reference, field), field)

            rows = [line for line in section.splitlines() if line.startswith("| ")]
            fact_names = [row.split(" | ")[0].removeprefix("| ") for row in rows]
            assert fact_names[1:4] == ["Field code", "Published column name", "Name"]
            code, column, name = (row.split(" | ")[1] for row in rows[1:4])
            assert code == f"`{field.name}`", field.name
            assert f"`{column_name(field)}`" in column, field.name
            assert reference.cell(str(field.title)) == name, field.name


class TestVocabularyEntries:
    def vocabulary_fields(self, schema: Schema) -> list[Field]:
        return [f for f in schema.fields if f.custom["vocabulary"] is not None]

    def test_scheme_and_collection_are_named_and_linked(
        self, schema: Schema, reference: FieldReference
    ) -> None:
        fields = self.vocabulary_fields(schema)
        assert fields

        for field in fields:
            named = field.custom["vocabulary"]
            section = section_of(entries_of(reference, field), field)

            assert f"<{named['scheme']}>" in section, field.name
            if named["collection"] is not None:
                assert f"<{named['collection']}>" in section, field.name

    def test_every_allowed_term_is_linked_to_its_concept(
        self,
        schema: Schema,
        reference: FieldReference,
        published_vocabularies: Vocabularies,
    ) -> None:
        for field in self.vocabulary_fields(schema):
            section = section_of(entries_of(reference, field), field)
            values = allowed_values(field, published_vocabularies)

            assert values, field.name
            for value in values:
                assert value.uri is not None
                assert f"[`{value.term}`]({value.uri})" in section, (
                    field.name,
                    value.term,
                )

    def test_a_fixed_value_is_listed_with_its_source(
        self,
        schema: Schema,
        reference: FieldReference,
        published_vocabularies: Vocabularies,
    ) -> None:
        for code in ("P9", "C9"):
            field = schema.get_field(code)
            assert field.custom["vocabulary"] is None
            section = section_of(entries_of(reference, field), field)

            for value in allowed_values(field, published_vocabularies):
                assert f"`{value.term}`" in section, code
                assert f"[`{value.term}`](" not in section, code
            assert "Fuchs et al. (2023), Appendix A" in section


def hostile_reference(
    schema: Schema,
    monkeypatch: pytest.MonkeyPatch,
    published_vocabularies: Vocabularies,
    uri: str = "https://example.org/concept",
    scheme: str | None = None,
    collection: str | None = None,
) -> FieldReference:
    """Build a reference whose vocabularies hold an address the network could send.

    Every vocabulary field gets one allowed value with the address ``uri``. The
    first vocabulary field with a collection is changed to name ``scheme`` and
    ``collection`` when they are given.
    """
    descriptor = schema.to_descriptor()
    if scheme is not None or collection is not None:
        entry = next(
            f for f in descriptor["fields"] if (f["vocabulary"] or {}).get("collection")
        )
        entry["vocabulary"]["scheme"] = scheme or entry["vocabulary"]["scheme"]
        entry["vocabulary"]["collection"] = (
            collection or entry["vocabulary"]["collection"]
        )
    value = AllowedValue(term="[x]", label="x", uri=uri, notation=None)
    monkeypatch.setattr(
        Vocabularies, "allowed_values", lambda self, vocabulary: (value,)
    )
    return FieldReference(Schema.from_descriptor(descriptor), published_vocabularies)


class TestAddresses:
    def test_brackets_and_parentheses_in_an_address_are_percent_encoded(self) -> None:
        address = FieldReference.address("https://example.org/a(b)[c]")

        assert address == "https://example.org/a%28b%29%5Bc%5D"

    def test_an_address_that_tries_to_start_another_link_stays_one_address(
        self,
    ) -> None:
        address = FieldReference.address(
            "https://example.org/a)[b](https://evil.example/"
        )

        assert address == "https://example.org/a%29%5Bb%5D%28https://evil.example/"
        assert ")[" not in address and "](" not in address

    @pytest.mark.parametrize(
        "address",
        ["https://w3id.org/ihfc-iugg/vocabularies/x/y_z", "http://example.org/a?b=c#d"],
    )
    def test_an_ordinary_web_address_is_unchanged(self, address: str) -> None:
        assert FieldReference.address(address) == address

    @pytest.mark.parametrize(
        "address",
        [
            "javascript:alert(1)",
            "ftp://example.org/x",
            "https://example.org/a b",
            "https://example.org/><script>",
            "https://example.org/`x`",
        ],
    )
    def test_anything_but_a_web_address_is_refused_naming_the_value(
        self, address: str
    ) -> None:
        with pytest.raises(ValueError, match="Not a web address") as caught:
            FieldReference.address(address)

        assert repr(address) in str(caught.value)

    def test_a_concept_address_cannot_end_its_link_early(
        self,
        schema: Schema,
        monkeypatch: pytest.MonkeyPatch,
        published_vocabularies: Vocabularies,
    ) -> None:
        reference = hostile_reference(
            schema,
            monkeypatch,
            published_vocabularies,
            uri="https://example.org/a(b)[c]",
        )

        markdown = reference.entries("child")

        assert "](https://example.org/a%28b%29%5Bc%5D)" in markdown

    @pytest.mark.parametrize(
        "uri", ["javascript:alert(1)", "https://example.org/a b", "https://x/`y`"]
    )
    def test_a_concept_address_that_is_not_a_web_address_stops_the_build(
        self,
        schema: Schema,
        monkeypatch: pytest.MonkeyPatch,
        published_vocabularies: Vocabularies,
        uri: str,
    ) -> None:
        reference = hostile_reference(schema, monkeypatch, published_vocabularies, uri)

        with pytest.raises(ValueError, match="Not a web address"):
            reference.entries("child")

    def test_a_scheme_address_that_would_close_its_autolink_stops_the_build(
        self,
        schema: Schema,
        monkeypatch: pytest.MonkeyPatch,
        published_vocabularies: Vocabularies,
    ) -> None:
        reference = hostile_reference(
            schema,
            monkeypatch,
            published_vocabularies,
            scheme="https://example.org/a> <b",
        )

        with pytest.raises(ValueError, match="Not a web address"):
            reference.entries("child")

    def test_a_collection_address_that_would_close_its_autolink_stops_the_build(
        self,
        schema: Schema,
        monkeypatch: pytest.MonkeyPatch,
        published_vocabularies: Vocabularies,
    ) -> None:
        reference = hostile_reference(
            schema,
            monkeypatch,
            published_vocabularies,
            collection="javascript:alert(1)",
        )

        with pytest.raises(ValueError, match="Not a web address"):
            reference.entries("child")


class TestSeparatorsAndEarlierSpellings:
    @pytest.mark.parametrize("code", ["C25", "C26", "C49"])
    def test_a_field_with_a_separator_gives_it(
        self, schema: Schema, reference: FieldReference, code: str
    ) -> None:
        field = schema.get_field(code)
        assert field.custom["separator"] is not None

        section = section_of(entries_of(reference, field), field)

        assert f"`{field.custom['separator']}`" in section

    def test_a_field_without_a_separator_says_nothing_of_one(
        self, schema: Schema, reference: FieldReference
    ) -> None:
        field = schema.get_field("P1")
        assert field.custom["separator"] is None

        section = section_of(entries_of(reference, field), field)

        assert "separat" not in section.lower()

    def test_an_earlier_spelling_is_given(
        self, schema: Schema, reference: FieldReference
    ) -> None:
        field = schema.get_field("C24")
        assert field.custom["earlierColumnNames"]

        section = section_of(entries_of(reference, field), field)

        for earlier in field.custom["earlierColumnNames"]:
            assert f"`{earlier}`" in section

    def test_guidance_is_given_when_the_field_has_it(
        self, schema: Schema, reference: FieldReference
    ) -> None:
        field = schema.get_field("C25")
        assert field.custom["guidance"] is not None

        section = section_of(entries_of(reference, field), field)

        assert "http://resource.geosciml.org/classifier/cgi/lithology" in section

    def test_range_is_shown_for_a_bounded_number(
        self, schema: Schema, reference: FieldReference
    ) -> None:
        field = schema.get_field("P1")
        low, high = field.constraints["minimum"], field.constraints["maximum"]

        section = section_of(entries_of(reference, field), field)

        assert f"{low} to {high}" in section

    def test_value_format_is_shown(
        self, schema: Schema, reference: FieldReference
    ) -> None:
        field = schema.get_field("C38")
        assert field.custom["valueFormat"] is not None

        section = section_of(entries_of(reference, field), field)

        assert f"`{field.custom['valueFormat']}`" in section


class TestTableCells:
    def test_a_pipe_in_a_fact_is_escaped_once(
        self, schema: Schema, published_vocabularies: Vocabularies
    ) -> None:
        descriptor = schema.to_descriptor()
        entry = next(f for f in descriptor["fields"] if f["name"] == "C43")
        entry["description"] = "left | right"
        reference = FieldReference(
            Schema.from_descriptor(descriptor), published_vocabularies
        )

        markdown = reference.entries("child")

        assert "left \\| right" in markdown
        assert "\\\\|" not in markdown


class TestFieldIndex:
    def test_one_row_per_field_in_order_linking_code_and_column_name(
        self, schema: Schema, reference: FieldReference
    ) -> None:
        rows = [
            line
            for line in reference.index().splitlines()
            if line.startswith("| {ref}")
        ]

        assert len(rows) == len(schema.fields) == 74
        for field, row in zip(schema.fields, rows, strict=True):
            name = column_name(field)
            code = f"{{ref}}`{field.name} <field-{field.name.lower()}>`"
            column = f"{{ref}}`{name} <field-{name.lower()}>`"
            assert code in row, field.name
            assert column in row, field.name
            assert str(field.title) in row.replace("\\", ""), field.name

    def test_a_pipe_in_a_cell_is_escaped(self, reference: FieldReference) -> None:
        assert reference.cell("a|b") == "a\\|b"


class TestRender:
    def test_the_index_call_is_replaced_by_the_index(
        self, reference: FieldReference
    ) -> None:
        text = "# Title\n\n{{ index() }}\n\nafter\n"

        result = reference.render(text)

        assert "index()" not in result
        assert result.startswith("# Title\n")
        assert result.endswith("\nafter\n")
        assert reference.index() in result

    @pytest.mark.parametrize("group", ["parent", "child", "assessment"])
    def test_an_entries_call_is_replaced_by_that_groups_entries(
        self, reference: FieldReference, group: str
    ) -> None:
        text = f'# Title\n\n{{{{ entries("{group}") }}}}\n'

        result = reference.render(text)

        assert "entries(" not in result
        assert reference.entries(group) in result

    def test_a_page_without_calls_is_unchanged(self, reference: FieldReference) -> None:
        text = "# Plain\n\nNothing to do.\n"

        assert reference.render(text) == text


class TestCopySchema:
    def test_the_schema_file_is_copied_into_the_documentation_source(
        self, schema: Schema, tmp_path: Path
    ) -> None:
        copy_schema(schema, tmp_path)

        copied = tmp_path / "reference" / "fields" / "ghfdb-field-schema.json"
        assert json.loads(copied.read_text(encoding="utf-8")) == schema.to_descriptor()

    def test_the_copy_is_ignored_by_git(self) -> None:
        root = Path(__file__).parents[3]
        ignored = (root / ".gitignore").read_text(encoding="utf-8").splitlines()

        assert "docs/reference/fields/ghfdb-field-schema.json" in ignored
