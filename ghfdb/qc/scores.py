"""The scores of the children of a dataset under the quality scheme."""

import numpy
import pandas
from frictionless import Schema

from ghfdb.fields import Vocabularies
from ghfdb.qc.borehole import BoreholeRules
from ghfdb.qc.check import Kind
from ghfdb.qc.probe import ProbeRules
from ghfdb.qc.rules import BOREHOLE, EXPLORATION_METHOD, PROBE_SENSING
from ghfdb.qc.scheme import (
    DECIMALS,
    FLAG_FIELDS,
    NOT_RECOGNIZED,
    PRESENT_CORRECTED,
    PRESENT_NOT_CORRECTED,
    PRESENT_NOT_SIGNIFICANT,
    Inputs,
    Score,
    Terms,
)
from ghfdb.qc.uncertainty import UScore

PROBE_RULES = "probe sensing"
BOREHOLE_RULES = "borehole and mine"
M_BOUNDARIES = (0.75, 0.50, 0.25)
# The problems that name a cell whose value is scored as empty.
BLANKING = (
    Kind.MISSING,
    Kind.WRONG_TYPE,
    Kind.OUT_OF_RANGE,
    Kind.NOT_IN_VOCABULARY,
    Kind.RULE,
)
COLUMNS = (
    "rules",
    "U",
    "T",
    "TC",
    "marked",
    "M",
    "flags",
    "code",
    "own_T",
    "own_TC",
    "own_T_marked",
    "own_TC_marked",
)


class Scores:
    """Routing and perturbation flags of the children of a dataset.

    Args:
        inputs: The scored fields of the children.
        terms: The terms the scheme's concepts resolve to.

    Attributes:
        inputs: The scored fields of the children.
        terms: The terms the scheme's concepts resolve to.
    """

    def __init__(self, inputs: Inputs, terms: Terms) -> None:
        self.inputs = inputs
        self.terms = terms

    @classmethod
    def build(
        cls,
        data: pandas.DataFrame,
        schema: Schema,
        problems: pandas.DataFrame | None = None,
        vocabularies: Vocabularies | None = None,
    ) -> "Scores":
        """Read the scored fields of a table of children.

        Args:
            data: One row per child and one column per field, named by field code.
            schema: The fields, which say where each takes its allowed values from.
            problems: The problem table of a check of ``data``. Every cell it names
                is scored as empty (see ``blank``).
            vocabularies: Where the allowed values come from. Without it, the
                vocabularies in the user's cache, downloaded when missing.

        Returns:
            The scores of the children.

        Raises:
            MissingSchemeError: A concept the scheme names is not an allowed value of
                its field.
            OSError: The vocabularies are not cached and cannot be downloaded.
        """
        terms = Terms(schema, vocabularies)
        return cls(Inputs(cls.blank(data, problems), terms), terms)

    @staticmethod
    def blank(
        data: pandas.DataFrame, problems: pandas.DataFrame | None
    ) -> pandas.DataFrame:
        """Empty the cells a problem table names.

        A problem of the kind missing, wrong type, out of range, not in vocabulary or
        rule blanks its cell, the field in ``code`` and never the one in ``related``.
        A problem with the kind of a column blanks nothing
        (docs/adr/0008-a-value-with-a-problem-is-scored-as-empty.md).

        Args:
            data: The children.
            problems: The problem table of a check of ``data``, or nothing.

        Returns:
            A copy of the children with the named cells empty.
        """
        cells = data.copy()
        if problems is None:
            return cells
        named = problems[problems["kind"].isin(BLANKING)]
        for code, rows in named.groupby("code")["row"]:
            if code in cells.columns:
                cells.loc[cells.index.isin(rows), code] = None
        return cells

    def routing(self) -> pandas.Series:
        """Choose the set of rules that scores each child.

        The exploration method decides, as in "Which rules score a child" of the
        overview of the quality scheme (docs/reference/quality-scheme/index.md).

        Returns:
            ``probe sensing`` or ``borehole and mine`` for each child, in the order of
            the children, and ``<NA>`` where the method selects no rules because it
            is other, unspecified or empty.
        """
        methods = self.inputs.first(self.inputs.concepts[EXPLORATION_METHOD])
        rules = pandas.Series(pandas.NA, index=methods.index, dtype="string")
        rules = rules.mask(methods.isin(PROBE_SENSING.concepts), PROBE_RULES)
        return rules.mask(methods.isin(BOREHOLE.concepts), BOREHOLE_RULES)

    def flags(self) -> pandas.Series:
        """Write the seven perturbation flags of each child.

        The characters are in the order S E T P V C R, from the correction fields C13
        to C19: the upper-case letter for present and corrected, the lower-case letter
        for present and not corrected, ``X`` for present and not significant, ``x`` for
        not recognised, and ``-`` for unspecified, empty or a term the field does not
        allow (docs/reference/quality-scheme/perturbation-flags.md, "How each flag is
        written").

        Returns:
            The flags of each child, in the order of the children.
        """
        flags = pandas.Series("", index=self.inputs.index, dtype="string")
        for code, letter in zip(FLAG_FIELDS, "SETPVCR", strict=True):
            characters = {
                PRESENT_CORRECTED: letter,
                PRESENT_NOT_CORRECTED: letter.lower(),
                PRESENT_NOT_SIGNIFICANT: "X",
                NOT_RECOGNIZED: "x",
            }
            state = self.inputs.first(self.inputs.concepts[code])
            flags = flags + state.map(characters).fillna("-").astype("string")
        return flags

    @staticmethod
    def m_score(t: Score, tc: Score) -> pandas.Series:
        """Grade the methods used to find each child's heat-flow value.

        The grade is the class of the product of the T-score and the TC-score rounded
        to three places: ``M1`` from 0.75, ``M2`` from 0.50, ``M3`` from 0.25 and ``M4``
        below, a product on a boundary taking the better class. An ``x`` follows the
        grade when either score carries the missing-information mark. The grade is
        ``Mx``, without the ``x`` mark, when either score is not determined
        (docs/reference/quality-scheme/m-score.md, "The product and its classes",
        "The missing-information mark" and "Not determined").

        Args:
            t: The T-score of each child.
            tc: The TC-score of each child.

        Returns:
            The M-score of each child, in the order of the children.
        """
        product = (t.value * tc.value).round(DECIMALS)
        figures = product.to_numpy(dtype="float64", na_value=numpy.nan)
        rank = 1 + numpy.sum([figures < edge for edge in M_BOUNDARIES], axis=0)
        marks = numpy.where((t.marked | tc.marked).fillna(False), "x", "")
        grade = pandas.Series(
            numpy.char.add(numpy.char.add("M", rank.astype(str)), marks),
            index=product.index,
        )
        return grade.where(product.notna(), "Mx").astype("string")

    @staticmethod
    def either(probe: Score, borehole: Score) -> Score:
        """Take the score of the rules that score each child.

        Args:
            probe: The score under the probe-sensing rules.
            borehole: The score under the borehole and mine rules.

        Returns:
            The score of the rules each child is routed to, ``<NA>`` for a child neither
            scores.
        """
        return Score(
            probe.value.fillna(borehole.value),
            probe.marked.fillna(borehole.marked),
        )

    def table(self) -> pandas.DataFrame:
        """Assemble the scores of every child.

        The quality code is the U-score, the M-score and the flags joined by points
        (docs/reference/quality-scheme/index.md, "The quality code"). A child no rules
        score has no T-score or TC-score and the M-score ``Mx``; an ``own`` score
        leaves the child's corrections out ("Scores of a child and of its
        measurements").

        Returns:
            One row for each child, in the order of the children, with the columns
            ``rules``, ``U``, ``T``, ``TC``, ``marked``, ``M``, ``flags``, ``code``,
            ``own_T``, ``own_TC``, ``own_T_marked`` and ``own_TC_marked``. The scores
            are floats and the marks booleans, both ``<NA>`` where not determined.
        """
        probe = ProbeRules(self.inputs)
        borehole = BoreholeRules(self.inputs)
        t = self.either(probe.t_score(), borehole.t_score())
        tc = self.either(probe.tc_score(), borehole.tc_score())
        own_t = self.either(probe.own_t_score(), borehole.own_t_score())
        own_tc = self.either(probe.own_tc_score(), borehole.own_tc_score())
        grade = self.m_score(t, tc)
        flags = self.flags()
        uncertainty = UScore(self.inputs).scores()
        table = pandas.DataFrame(
            {
                "rules": self.routing(),
                "U": uncertainty,
                "T": t.value,
                "TC": tc.value,
                "marked": (t.marked | tc.marked).where(grade != "Mx"),
                "M": grade,
                "flags": flags,
                "code": uncertainty + "." + grade + "." + flags,
                "own_T": own_t.value,
                "own_TC": own_tc.value,
                "own_T_marked": own_t.marked,
                "own_TC_marked": own_tc.marked,
            },
            index=self.inputs.index,
        )
        return table[list(COLUMNS)]
