from typing import Any

import pandas
from conftest import column_children, field_concepts
from rdflib import URIRef

from ghfdb.fields import Field
from ghfdb.fields.schema import FieldConcepts
from ghfdb.qc.inputs import Inputs
from ghfdb.qc.penalties import Classes, Criterion, Group
from ghfdb.qc.rules import Condition
from ghfdb.qc.ruleset import RuleSet

RED, GREEN = URIRef("c:red"), URIRef("c:green")
SMALL, LARGE = URIRef("c:small"), URIRef("c:large")
TILTED, SURFACE_METHOD = URIRef("c:tilted"), URIRef("c:surface")
NAMES: dict[str, FieldConcepts] = {
    Field.tc_location: field_concepts({"[red]": RED, "[green]": GREEN}),
    Field.tc_method: field_concepts({"[small]": SMALL, "[large]": LARGE}),
    Field.corr_T_flag: field_concepts({"[tilted]": TILTED, "[other]": "c:other"}),
}
LOCATION = Criterion(
    "x.location",
    "A location",
    Classes((Field.tc_location,), (Group(0.0, (RED,)), Group(-0.1, (GREEN,)))),
    "Table 1",
)
METHOD = Criterion(
    "x.method",
    "A method",
    Classes((Field.tc_method,), (Group(0.1, (SMALL,)), Group(-0.1, (LARGE,)))),
    "Table 1",
)
ALONE = Criterion(
    "x.method-alone",
    "A method scored alone",
    Classes((Field.tc_method,), (Group(-0.3, (SMALL, LARGE)),)),
    "Table 1",
)
CORRECTED = Condition(Field.corr_T_flag, (TILTED,))
SURFACE = Condition(Field.explo_method, (SURFACE_METHOD,))


class Rules(RuleSet):
    criteria = (LOCATION, METHOD)
    waivers = {LOCATION.identifier: CORRECTED}
    stand_ins = {METHOD.identifier: ALONE}
    conditions = (SURFACE,)
    extra_fields = (Field.T_number, Field.tc_location)


def children(**columns: list[Any]) -> pandas.DataFrame:
    return column_children(**columns)


class TestRuleSet:
    def test_reads_every_field_once_that_a_criterion_a_waiver_or_the_rules_read(
        self,
    ) -> None:
        assert Rules.reads() == (
            Field.tc_location,
            Field.tc_method,
            Field.corr_T_flag,
            Field.explo_method,
            Field.T_number,
        )

    def test_names_every_concept_once_that_a_criterion_or_a_condition_names(
        self,
    ) -> None:
        assert Rules.concepts() == (
            (Field.tc_location, RED),
            (Field.tc_location, GREEN),
            (Field.tc_method, SMALL),
            (Field.tc_method, LARGE),
            (Field.corr_T_flag, TILTED),
            (Field.explo_method, SURFACE_METHOD),
        )

    def test_a_waiver_applies_to_the_child_and_not_to_the_measurement_on_its_own(
        self,
    ) -> None:
        data = children(C42=["[green]", "[green]"], C12=["[tilted]", None])
        rules = Rules(Inputs(data, NAMES), numpy_true(2))

        child, alone = rules.penalties(Rules.criteria)

        assert child[0].value.tolist() == [0.0, -0.1]
        assert alone[0].value.tolist() == [-0.1, -0.1]

    def test_a_stand_in_scores_the_measurement_on_its_own_in_place_of_a_criterion(
        self,
    ) -> None:
        data = children(C43=["[small]", "[large]"])
        rules = Rules(Inputs(data, NAMES), numpy_true(2))

        child, alone = rules.penalties(Rules.criteria)

        assert child[1].value.tolist() == [0.1, -0.1]
        assert alone[1].value.tolist() == [-0.3, -0.3]

    def test_a_correction_is_read_at_the_first_value_of_its_field(self) -> None:
        data = children(C12=[["[tilted]", "[other]"], ["[other]", "[tilted]"], None])
        rules = Rules(Inputs(data, NAMES), numpy_true(3))

        assert rules.has(CORRECTED).tolist() == [True, False, False]


def numpy_true(length: int) -> Any:
    return pandas.Series(True, index=range(length)).to_numpy()
