"""The cross-field rules: what a child's fields must say together.

The field schema checks each field on its own. A cross-field rule relates two or more
fields of the same child, for example "a child explored by drilling has its interval
bottom filled". Every rule is declared here, in Python, and listed in ``RULES``, which
``DatasetCheck`` applies after the field check. Each broken rule is one line of kind
``rule`` in the problem table, with the rule's identifier in ``rule`` and the field
that decided the rule applies in ``related``.

A rule names the vocabulary values it needs by their concept, such as
``concepts.tc_source["core-samples"]`` from ``ghfdb.vocabularies``, never by their term.
``DatasetCheck`` turns each concept into the term the field accepts, using the
vocabularies the field schema was built from, and refuses a concept the field does not
accept. A collection of the field's scheme stands for its members.

To add a rule of an existing kind, write its ``Example`` and add it to ``RULES``, with a
new identifier that is never reused. The kinds, and how to add a new one, are in
``ghfdb.qc.engine.rule_kinds``.
"""

from ghfdb.fields import Field
from ghfdb.qc.engine.rule_kinds import (
    AllowedWhen,
    Condition,
    Domain,
    Example,
    RequiredWhen,
    Rule,
)
from ghfdb.vocabularies import concepts

EXPLORATION_METHOD = Field.explo_method
METHOD = concepts.explo_method
LOCATION = concepts.tc_location
SOURCE = concepts.tc_source
TEMPERATURE = concepts.T_method_top
CONDUCTIVITY = concepts.tc_method

BOREHOLE = Domain(
    "B",
    EXPLORATION_METHOD,
    (
        METHOD.drilling,
        METHOD["drilling-clustering"],
        METHOD.mining,
        METHOD.tunneling,
        METHOD.indirect,
    ),
    "a borehole and mine method",
    "borehole and mine",
)
PROBE_SENSING = Domain(
    "S",
    EXPLORATION_METHOD,
    (
        METHOD["probing-onshore"],
        METHOD["probing-offshore"],
        METHOD["probing-clustering"],
    ),
    "a probe-sensing method",
    "probe sensing",
)


CF_1 = RequiredWhen(
    identifier="CF-1",
    statement=(
        "A child explored through a borehole, a mine or a tunnel, or estimated "
        "indirectly, has every field mandatory for borehole and mine data filled."
    ),
    source="fuchs-2023-table-4",
    reasoning=(
        "Table 4 of Fuchs et al. (2023) marks these fields mandatory for borehole and "
        "mine data only, so a child of that domain must fill them. Which exploration "
        "methods belong to the domain is set out with the rules, and is open to "
        "confirmation by the data assessment team."
    ),
    example=Example(
        {Field.explo_method: METHOD.drilling, Field.q_bottom: None}, (Field.q_bottom,)
    ),
    domain=BOREHOLE,
)
CF_2 = RequiredWhen(
    identifier="CF-2",
    statement=(
        "A child explored by probing has every field mandatory for probe sensing "
        "filled."
    ),
    source="fuchs-2023-table-4",
    reasoning=(
        "Table 4 of Fuchs et al. (2023) marks these fields mandatory for probe sensing "
        "only, so a child of that domain must fill them. Which exploration methods "
        "belong to the domain is set out with the rules, and is open to confirmation "
        "by the data assessment team."
    ),
    example=Example(
        {Field.explo_method: METHOD["probing-onshore"], Field.probe_penetration: None},
        (Field.probe_penetration,),
    ),
    domain=PROBE_SENSING,
)
CF_3 = AllowedWhen(
    identifier="CF-3",
    statement=(
        "A thermal conductivity location of literature or unspecified is allowed only "
        "when the thermal conductivity source is assumed from literature."
    ),
    source="fuchs-2023-appendix-a",
    reasoning=(
        "Appendix A of Fuchs et al. (2023) allows the location literature or "
        "unspecified only if the source is assumed from literature: conductivity "
        "measured on samples or in situ was measured somewhere, so its location is "
        "known."
    ),
    example=Example(
        {
            Field.tc_location: LOCATION.literature,
            Field.tc_source: SOURCE["core-samples"],
        },
        (Field.tc_source,),
    ),
    when=Condition(Field.tc_location, (LOCATION.literature,)),
    then=Condition(Field.tc_source, (SOURCE["assumed-from-literature"],)),
)

CF_4 = AllowedWhen(
    identifier="CF-4",
    statement=(
        "A child whose temperature method at the top or at the bottom is the enhanced "
        "geothermal response test has the thermal conductivity method probe - pulse "
        "technique."
    ),
    source="fuchs-2025-template-2026-03",
    reasoning=(
        "Section 6.1 of the description of version 2026.03 of the submission template "
        "asks that, when the enhanced geothermal response test is used as the "
        "temperature method, the thermal conductivity method is the probe pulse "
        "technique, so that thermal conductivity is reported consistently."
    ),
    example=Example(
        {
            Field.T_method_top: TEMPERATURE.EGRT,
            Field.tc_method: CONDUCTIVITY.pointSource,
        },
        (Field.tc_method,),
    ),
    when=Condition(Field.T_method_top, (TEMPERATURE.EGRT,)),
    then=Condition(Field.tc_method, (CONDUCTIVITY.probePulse,)),
    alternatives=(Condition(Field.T_method_bottom, (TEMPERATURE.EGRT,)),),
)

RULES: tuple[Rule, ...] = (CF_1, CF_2, CF_3, CF_4)
