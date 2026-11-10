"""The scores of the children of a dataset under the quality scheme."""

import numpy
import pandas
from frictionless import Schema

from ghfdb.fields import Field, Vocabularies
from ghfdb.qc.borehole import BoreholeRules
from ghfdb.qc.check import Kind
from ghfdb.qc.concepts import (
    NOT_RECOGNIZED,
    PRESENT_CORRECTED,
    PRESENT_NOT_CORRECTED,
    PRESENT_NOT_SIGNIFICANT,
    UNSPECIFIED_CORRECTION,
)
from ghfdb.qc.criteria import term_uris
from ghfdb.qc.inputs import Inputs
from ghfdb.qc.penalties import SCORE_DECIMALS, Band, Score
from ghfdb.qc.probe import ProbeRules
from ghfdb.qc.rules import BOREHOLE, EXPLORATION_METHOD, PROBE_SENSING
from ghfdb.qc.uncertainty import UScore

# The class of the product of the T-score and the TC-score: M1 from 0.75, M2 from 0.50,
# M3 from 0.25 and M4 below. A product on an edge takes the better class.
PRODUCT_CLASSES = (
    Band(1, 0.75, inclusive=True),
    Band(2, 0.50, inclusive=True),
    Band(3, 0.25, inclusive=True),
    Band(4),
)
# The correction field of each perturbation flag, in the order the flags are written.
FLAGS = {
    Field.corr_S_flag: "S",
    Field.corr_E_flag: "E",
    Field.corr_TOPO_flag: "T",
    Field.corr_PAL_flag: "P",
    Field.corr_SUR_flag: "V",
    Field.corr_CONV_flag: "C",
    Field.corr_HR_flag: "R",
}
# The problems that name a cell whose value is scored as empty.
BLANKING = (
    Kind.MISSING,
    Kind.WRONG_TYPE,
    Kind.OUT_OF_RANGE,
    Kind.NOT_IN_VOCABULARY,
    Kind.RULE,
)
# The columns of the table of scores, in order.
SCORE_COLUMNS = (
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
# The columns a report shows for each child.
REPORT_COLUMNS = ("rules", "U", "T", "TC", "M", "flags", "code")


class Scores:
    """Routing, perturbation flags and grades of the children of a dataset.

    The exploration method routes each child to a set of rules once, and both sets of
    rules are given the children they score.

    Args:
        inputs: The scored fields of the children.

    Attributes:
        inputs: The scored fields of the children.
        routing: The name of the set of rules that scores each child, in the order of
            the children, ``<NA>`` where the exploration method selects none because it
            is other, unspecified or empty.
        probe: The probe-sensing rules.
        borehole: The borehole and mine rules.
    """

    def __init__(self, inputs: Inputs) -> None:
        self.inputs = inputs
        methods = inputs.first(inputs.concepts(EXPLORATION_METHOD))
        routing = pandas.Series(pandas.NA, index=methods.index, dtype="string")
        for domain in (PROBE_SENSING, BOREHOLE):
            routing = routing.mask(methods.isin(domain.concepts), domain.rules)
        self.routing = routing
        self.probe = ProbeRules(inputs, routing.isin([PROBE_SENSING.rules]).to_numpy())
        self.borehole = BoreholeRules(inputs, routing.isin([BOREHOLE.rules]).to_numpy())

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
        uris = term_uris(schema, cls.concepts(), vocabularies)
        return cls(Inputs(cls.blank(data, problems), uris))

    @staticmethod
    def concepts() -> tuple[tuple[str, str], ...]:
        """List every concept the scheme names, with its field.

        Returns:
            The concepts of the exploration methods, of the perturbation flags and of
            both sets of rules, each once.
        """
        methods = tuple(
            (EXPLORATION_METHOD, uri)
            for domain in (PROBE_SENSING, BOREHOLE)
            for uri in domain.concepts
        )
        flags = tuple(
            (field, uri) for field in FLAGS for uri in Scores.flag_characters("S")
        )
        return tuple(
            dict.fromkeys(
                (*methods, *flags, *ProbeRules.concepts(), *BoreholeRules.concepts())
            )
        )

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

    @staticmethod
    def flag_characters(letter: str) -> dict[str, str]:
        """Say how each state of a correction is written in a flag.

        Args:
            letter: The flag's letter.

        Returns:
            The character of each correction concept: the upper-case letter for present
            and corrected, the lower-case letter for present and not corrected, ``X``
            for present and not significant, ``x`` for not recognised and ``-`` for
            unspecified (docs/reference/quality-scheme/perturbation-flags.md, "How
            each flag is written").
        """
        return {
            PRESENT_CORRECTED: letter,
            PRESENT_NOT_CORRECTED: letter.lower(),
            PRESENT_NOT_SIGNIFICANT: "X",
            NOT_RECOGNIZED: "x",
            UNSPECIFIED_CORRECTION: "-",
        }

    def flags(self) -> pandas.Series:
        """Write the seven perturbation flags of each child.

        A correction that is empty, or a term its field does not allow, is written
        ``-`` like an unspecified one.

        Returns:
            The flags of each child, in the order of the children.
        """
        flags = pandas.Series("", index=self.inputs.index, dtype="string")
        for field, letter in FLAGS.items():
            state = self.inputs.first(self.inputs.concepts(field))
            characters = Inputs.translate(state, self.flag_characters(letter))
            flags = flags + characters.fillna("-")
        return flags

    @staticmethod
    def grades(t: Score, tc: Score) -> pandas.Series:
        """Grade the methods used to find each child's heat-flow value.

        The grade is the class of the product of the T-score and the TC-score rounded
        to three places (``PRODUCT_CLASSES``). An ``x`` follows the grade when either
        score carries the missing-information mark. The grade is ``Mx``, without the
        ``x`` mark, when either score is not determined
        (docs/reference/quality-scheme/m-score.md, "The product and its classes",
        "The missing-information mark" and "Not determined").

        Args:
            t: The T-score of each child.
            tc: The TC-score of each child.

        Returns:
            The M-score of each child, in the order of the children.
        """
        product = (t.value * tc.value).round(SCORE_DECIMALS)
        figures = product.to_numpy(dtype="float64", na_value=numpy.nan)
        rank = Band.select(PRODUCT_CLASSES, pandas.Series(figures), 0).astype(int)
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
            One row for each child, in the order of the children, with the
            ``SCORE_COLUMNS``. The scores are floats and the marks booleans, both
            ``<NA>`` where not determined.
        """
        probe, borehole = self.probe.scores(), self.borehole.scores()
        t = self.either(probe.t, borehole.t)
        tc = self.either(probe.tc, borehole.tc)
        own_t = self.either(probe.own_t, borehole.own_t)
        own_tc = self.either(probe.own_tc, borehole.own_tc)
        grade = self.grades(t, tc)
        flags = self.flags()
        uncertainty = UScore(self.inputs).grades()
        table = pandas.DataFrame(
            {
                "rules": self.routing,
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
        return table[list(SCORE_COLUMNS)]
