import re
from dataclasses import replace
from pathlib import Path

import pytest
from extensions.field_reference import (
    FieldReference,
    copy_schema,
    replace_markers,
)

from ghfdb.fields import AllowedValue, Field, FieldSchema, VocabularyRelease

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
def schema() -> FieldSchema:
    return FieldSchema.load()


@pytest.fixture(scope="module")
def reference(schema: FieldSchema) -> FieldReference:
    return FieldReference(schema)


def section_of(markdown: str, field: Field) -> str:
    """Return the text of one field's entry on a group's page."""
    marker = f"(field-{field.code.lower()})=\n"
    start = markdown.index(marker)
    following = markdown.find("\n\n(field-", start + len(marker))
    return markdown[start:] if following == -1 else markdown[start:following]


class TestFieldReferenceEntries:
    @pytest.mark.parametrize("group", ["parent", "child", "assessment"])
    def test_each_field_has_one_entry_on_its_group_page_in_code_order(
        self, schema: FieldSchema, reference: FieldReference, group: str
    ) -> None:
        markdown = reference.entries(group)

        codes = re.findall(r"^\(field-([a-z]\d+)\)=$", markdown, re.MULTILINE)
        expected = [f.code.lower() for f in schema if f.group == group]
        assert codes == expected

    def test_the_three_groups_hold_all_seventy_fields(
        self, schema: FieldSchema, reference: FieldReference
    ) -> None:
        total = sum(
            len(re.findall(r"^\(field-[a-z]\d+\)=$", reference.entries(g), re.M))
            for g in ("parent", "child", "assessment")
        )

        assert total == len(schema) == 70

    def test_each_entry_has_a_target_for_its_code_and_for_its_column_name(
        self, schema: FieldSchema, reference: FieldReference
    ) -> None:
        for field in schema:
            section = section_of(reference.entries(field.group), field)

            assert f"(field-{field.code.lower()})=\n" in section, field.code
            assert f"(field-{field.column_name.lower()})=\n" in section, field.code

    def test_no_two_fields_share_a_target(self, schema: FieldSchema) -> None:
        targets = [f.code.lower() for f in schema]
        targets += [f.column_name.lower() for f in schema]

        assert len(set(targets)) == len(targets)

    def test_the_heading_sits_one_level_below_the_page_title(
        self, schema: FieldSchema, reference: FieldReference
    ) -> None:
        for field in schema:
            section = section_of(reference.entries(field.group), field)

            headings = re.findall(r"^(#+) ", section, re.MULTILINE)
            assert headings == ["##"], field.code
            assert field.code in section.split("\n## ", 1)[1].split("\n", 1)[0]

    def test_every_entry_names_its_column_name_and_links_each_decision_it_cites(
        self, schema: FieldSchema, reference: FieldReference
    ) -> None:
        for field in schema:
            section = section_of(reference.entries(field.group), field)

            assert f"`{field.column_name}`" in section, field.code
            for key in ALWAYS_SHOWN:
                source = field.sources[key]
                if source.startswith("decision:"):
                    label = source.removeprefix("decision:")
                    assert f"[Decision {label}]({GITHUB_DECISIONS})" in section

    def test_a_missing_fact_shows_an_em_dash(
        self, schema: FieldSchema, reference: FieldReference
    ) -> None:
        field = schema["C25"]
        assert field.unit is None

        section = section_of(reference.entries(field.group), field)

        assert "| Unit | — |" in section

    def test_vocabulary_sources_name_the_release_and_link_its_doi(
        self, schema: FieldSchema, reference: FieldReference
    ) -> None:
        field = schema["C43"]

        section = section_of(reference.entries(field.group), field)

        label = f"[IHFC Controlled Vocabularies v{schema.release.version}]"
        assert f"{label}(https://doi.org/{schema.release.doi})" in section

    def test_the_decision_source_links_to_the_recorded_decisions(
        self, schema: FieldSchema, reference: FieldReference
    ) -> None:
        field = schema["P1"]
        decision = field.sources["type"]
        assert decision.startswith("decision:")

        section = section_of(reference.entries(field.group), field)

        label = decision.removeprefix("decision:")
        assert f"[Decision {label}]({GITHUB_DECISIONS})" in section


class TestFactOrder:
    def test_every_entry_opens_with_code_column_name_and_name_in_that_order(
        self, reference: FieldReference, schema: FieldSchema
    ) -> None:
        for field in schema:
            values = [value for _, value, _ in reference.rows(field)[:3]]

            assert field.code in values[0], field.code
            assert field.column_name in values[1], field.code
            assert reference.cell(field.name) == values[2], field.code


class TestVocabularyEntries:
    def vocabulary_fields(self, schema: FieldSchema) -> list[Field]:
        return [f for f in schema if f.vocabulary is not None]

    def test_scheme_and_release_and_collection_are_named_and_linked(
        self, schema: FieldSchema, reference: FieldReference
    ) -> None:
        fields = self.vocabulary_fields(schema)
        assert fields

        for field in fields:
            assert field.vocabulary is not None
            section = section_of(reference.entries(field.group), field)

            assert f"<{field.vocabulary.scheme}>" in section, field.code
            if field.vocabulary.collection is not None:
                assert f"<{field.vocabulary.collection}>" in section, field.code
            assert schema.release.version in section, field.code
            assert f"https://doi.org/{schema.release.doi}" in section, field.code

    def test_every_allowed_term_is_linked_to_its_concept(
        self, schema: FieldSchema, reference: FieldReference
    ) -> None:
        for field in self.vocabulary_fields(schema):
            section = section_of(reference.entries(field.group), field)

            assert field.allowed_values, field.code
            for value in field.allowed_values:
                assert value.uri is not None
                assert f"[`{value.term}`]({value.uri})" in section, (
                    field.code,
                    value.term,
                )

    def test_a_fixed_value_is_listed_with_its_source(
        self, schema: FieldSchema, reference: FieldReference
    ) -> None:
        for code in ("P9", "C9"):
            field = schema[code]
            assert field.vocabulary is None
            section = section_of(reference.entries(field.group), field)

            for value in field.allowed_values:
                assert f"`{value.term}`" in section, code
                assert f"[`{value.term}`](" not in section, code
            assert "Fuchs et al. (2023), Appendix A" in section


class TestReleaseAddresses:
    def test_brackets_and_parentheses_in_a_concept_uri_cannot_end_its_link(
        self, schema: FieldSchema, reference: FieldReference
    ) -> None:
        field = schema["C43"]
        value = AllowedValue(
            term="x",
            label="x",
            uri="https://example.org/a)[b](https://evil.example/",
            notation=None,
        )

        markdown = reference.entry(replace(field, allowed_values=(value,)))

        assert "https://example.org/a%29%5Bb%5D%28https://evil.example/" in markdown
        assert "](https://evil.example/" not in markdown

    @pytest.mark.parametrize(
        "uri",
        [
            "javascript:alert(1)",
            "https://example.org/a b",
            "https://example.org/><script>",
            "https://example.org/`x`",
        ],
    )
    def test_a_concept_uri_that_is_not_a_web_address_is_refused(
        self, schema: FieldSchema, reference: FieldReference, uri: str
    ) -> None:
        field = schema["C43"]
        value = AllowedValue(term="x", label="x", uri=uri, notation=None)

        with pytest.raises(ValueError, match="Not a web address"):
            reference.entry(replace(field, allowed_values=(value,)))

    def test_a_scheme_uri_that_would_close_its_autolink_is_refused(
        self, schema: FieldSchema, reference: FieldReference
    ) -> None:
        field = schema["C43"]
        assert field.vocabulary is not None
        vocabulary = replace(field.vocabulary, scheme="https://example.org/a> <b")

        with pytest.raises(ValueError, match="Not a web address"):
            reference.entry(replace(field, vocabulary=vocabulary))

    def test_a_release_doi_cannot_end_its_link_or_inject_markup(
        self, schema: FieldSchema
    ) -> None:
        release = VocabularyRelease(
            version="2026.1_*", doi="10.1/a)[b](https://evil.example/"
        )
        hostile = FieldSchema(schema.path, release, tuple(schema))

        markdown = FieldReference(hostile).entry(schema["C43"])

        assert not re.search(r"(?<!\\)\]\(https://evil", markdown)
        assert "v2026.1\\_\\*" in markdown


class TestSeparatorsAndEarlierSpellings:
    @pytest.mark.parametrize("code", ["C25", "C26", "C49"])
    def test_a_field_with_a_separator_gives_it(
        self, schema: FieldSchema, reference: FieldReference, code: str
    ) -> None:
        field = schema[code]
        assert field.separator is not None

        section = section_of(reference.entries(field.group), field)

        assert f"`{field.separator}`" in section

    def test_a_field_without_a_separator_says_nothing_of_one(
        self, schema: FieldSchema, reference: FieldReference
    ) -> None:
        field = schema["P1"]
        assert field.separator is None

        section = section_of(reference.entries(field.group), field)

        assert "separat" not in section.lower()

    @pytest.mark.parametrize("code", ["C46", "C49"])
    def test_an_earlier_spelling_is_given(
        self, schema: FieldSchema, reference: FieldReference, code: str
    ) -> None:
        field = schema[code]
        assert field.earlier_column_names

        section = section_of(reference.entries(field.group), field)

        for earlier in field.earlier_column_names:
            assert f"`{earlier}`" in section

    def test_guidance_is_given_when_the_field_has_it(
        self, schema: FieldSchema, reference: FieldReference
    ) -> None:
        field = schema["C25"]
        assert field.guidance is not None

        section = section_of(reference.entries(field.group), field)

        assert "http://resource.geosciml.org/classifier/cgi/lithology" in section

    def test_range_is_shown_for_a_bounded_number(
        self, schema: FieldSchema, reference: FieldReference
    ) -> None:
        field = schema["P1"]

        section = section_of(reference.entries(field.group), field)

        assert f"{field.minimum} to {field.maximum}" in section

    def test_value_format_is_shown(
        self, schema: FieldSchema, reference: FieldReference
    ) -> None:
        field = schema["C38"]
        assert field.value_format is not None

        section = section_of(reference.entries(field.group), field)

        assert f"`{field.value_format}`" in section


class TestTableCells:
    def test_a_pipe_in_a_fact_is_escaped_once(
        self, reference: FieldReference, schema: FieldSchema
    ) -> None:
        field = replace(schema["C43"], meaning="left | right")

        markdown = reference.entry(field)

        assert "left \\| right" in markdown
        assert "\\\\|" not in markdown


class TestFieldIndex:
    def test_one_row_per_field_in_order_linking_code_and_column_name(
        self, schema: FieldSchema, reference: FieldReference
    ) -> None:
        rows = [
            line
            for line in reference.index().splitlines()
            if line.startswith("| {ref}")
        ]

        assert len(rows) == len(schema) == 70
        for field, row in zip(schema, rows, strict=True):
            code = f"{{ref}}`{field.code} <field-{field.code.lower()}>`"
            column = f"{{ref}}`{field.column_name} <field-{field.column_name.lower()}>`"
            assert code in row, field.code
            assert column in row, field.code
            assert field.name in row.replace("\\", ""), field.code

    def test_a_pipe_in_a_cell_is_escaped(self, reference: FieldReference) -> None:
        assert reference.cell("a|b") == "a\\|b"


class TestReplaceMarkers:
    def test_the_index_marker_line_is_replaced(self, reference: FieldReference) -> None:
        text = "# Title\n\n{field-index}\n\nafter\n"

        result = replace_markers(text, reference)

        assert "{field-index}" not in result
        assert result.startswith("# Title\n")
        assert result.endswith("\nafter\n")
        assert reference.index() in result

    @pytest.mark.parametrize("group", ["parent", "child", "assessment"])
    def test_an_entries_marker_is_replaced_by_that_groups_entries(
        self, reference: FieldReference, group: str
    ) -> None:
        text = f"# Title\n\n{{field-entries}} {group}\n"

        result = replace_markers(text, reference)

        assert "{field-entries}" not in result
        assert reference.entries(group) in result

    def test_a_marker_inside_a_line_is_left_alone(
        self, reference: FieldReference
    ) -> None:
        text = "Write `{field-index}` where the table goes.\n"

        assert replace_markers(text, reference) == text

    def test_a_page_without_markers_is_unchanged(
        self, reference: FieldReference
    ) -> None:
        text = "# Plain\n\nNothing to do.\n"

        assert replace_markers(text, reference) == text


class TestCopySchema:
    def test_the_schema_file_is_copied_into_the_documentation_source(
        self, schema: FieldSchema, tmp_path: Path
    ) -> None:
        copy_schema(schema, tmp_path)

        copied = tmp_path / "reference" / "fields" / "ghfdb-field-schema.json"
        assert copied.read_bytes() == schema.path.read_bytes()

    def test_the_copy_is_ignored_by_git(self) -> None:
        root = Path(__file__).parents[3]
        ignored = (root / ".gitignore").read_text(encoding="utf-8").splitlines()

        assert "docs/reference/fields/ghfdb-field-schema.json" in ignored
