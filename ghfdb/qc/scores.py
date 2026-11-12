"""The scores of the children of a dataset under the quality scheme."""

import numpy
import pandas
from frictionless import Schema
from rdflib import URIRef

from ghfdb.fields.schema import FieldConcepts
from ghfdb.qc.check import Kind
from ghfdb.qc.engine.inputs import Inputs
from ghfdb.qc.engine.rule_kinds import Domain
from ghfdb.qc.engine.tables import SCORE_DECIMALS, Band, Score
from ghfdb.qc.scheme.borehole import BoreholeAndMine
from ghfdb.qc.scheme.domains import BOREHOLE, EXPLORATION_METHOD, PROBE_SENSING
from ghfdb.qc.scheme.grades import FLAGS, PRODUCT_CLASSES, UScore, flag_characters
from ghfdb.qc.scheme.probe import ProbeSensing
from ghfdb.vocabularies import Vocabularies

# The problems that name a cell whose value is scored as empty.
BLANKING = (
    Kind.MISSING,
    Kind.WRONG_TYPE,
    Kind.OUT_OF_RANGE,
    Kind.NOT_IN_VOCABULARY,
    Kind.RULE,
)
# The columns of the table of scores, in order. ``Scores.table`` gives the values of
# each in this order.
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


class Scores:
    """Routing, perturbation flags and grades of the children of a dataset.

    The exploration method routes each child to the scoring of a domain once, and both
    scorings are given the children they score.

    Args:
        inputs: The scored fields of the children.

    Attributes:
        inputs: The scored fields of the children.
        routing: The name of the scoring that scores each child, in the order of
            the children, ``<NA>`` where the exploration method selects none because it
            is other, unspecified or empty.
        probe: The scoring of the probe-sensing domain.
        borehole: The scoring of the borehole and mine domain.
    """

    def __init__(self, inputs: Inputs) -> None:
        self.inputs = inputs
        methods = inputs.first(inputs.concepts(EXPLORATION_METHOD))
        routing = pandas.Series(pandas.NA, index=methods.index, dtype="string")
        for domain in (PROBE_SENSING, BOREHOLE):
            members = inputs.expand(EXPLORATION_METHOD, domain.concepts)
            routing = routing.mask(methods.isin(members), domain.scoring)
        self.routing = routing
        self.probe = ProbeSensing(
            inputs, self.scored(PROBE_SENSING, ProbeSensing.reads())
        )
        self.borehole = BoreholeAndMine(
            inputs, self.scored(BOREHOLE, BoreholeAndMine.reads())
        )

    def scored(self, domain: Domain, reads: tuple[str, ...]) -> numpy.ndarray:
        """Find the children that the scoring of a domain scores.

        A child that is routed to the scoring, yet leaves every field it reads empty, is
        not scored: its scores are not determined
        (docs/reference/quality-scheme/m-score.md, "Not determined").

        Args:
            domain: The exploration methods the scoring scores.
            reads: The fields the scoring reads, other than the exploration method.

        Returns:
            Whether the scoring scores each child, in the order of the children.
        """
        routed = self.routing.isin([domain.scoring]).to_numpy(dtype=bool)
        return numpy.asarray(routed & self.inputs.any_filled(reads), dtype=bool)

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
            MissingSchemeError: A concept the scheme names is neither an allowed value
                of its field nor a collection of the field's scheme.
            OSError: The vocabularies are not cached and cannot be downloaded.
        """
        files = Vocabularies() if vocabularies is None else vocabularies
        resolved = FieldConcepts.resolve(schema, cls.concepts(), files)
        return cls(Inputs(cls.blank(data, problems), resolved))

    @staticmethod
    def concepts() -> tuple[tuple[str, URIRef], ...]:
        """List every concept the scheme names, with its field.

        Returns:
            The concepts of the exploration methods, of the perturbation flags and of
            both scorings, each once.
        """
        methods = tuple(
            (EXPLORATION_METHOD, concept)
            for domain in (PROBE_SENSING, BOREHOLE)
            for concept in domain.concepts
        )
        flags = tuple(
            (field, concept) for field in FLAGS for concept in flag_characters("S")
        )
        return tuple(
            dict.fromkeys(
                (
                    *methods,
                    *flags,
                    *ProbeSensing.concepts(),
                    *BoreholeAndMine.concepts(),
                )
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
            characters = Inputs.translate(state, flag_characters(letter))
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
        """Take the score of the scoring that scores each child.

        Args:
            probe: The score under the probe-sensing scoring.
            borehole: The score under the borehole and mine scoring.

        Returns:
            The score of the scoring each child is routed to, ``<NA>`` for a child
            neither scores.
        """
        return Score(
            probe.value.fillna(borehole.value),
            probe.marked.fillna(borehole.marked),
        )

    def table(self) -> pandas.DataFrame:
        """Assemble the scores of every child.

        The quality code is the U-score, the M-score and the flags joined by points
        (docs/reference/quality-scheme/index.md, "The quality code"). A child that no
        scoring scores has no T-score or TC-score and the M-score ``Mx``; an ``own``
        score leaves the child's corrections out ("Scores of a child and of its
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
        columns = (
            self.routing,
            uncertainty,
            t.value,
            tc.value,
            (t.marked | tc.marked).where(grade != "Mx"),
            grade,
            flags,
            uncertainty + "." + grade + "." + flags,
            own_t.value,
            own_tc.value,
            own_t.marked,
            own_tc.marked,
        )
        return pandas.DataFrame(
            dict(zip(SCORE_COLUMNS, columns, strict=True)), index=self.inputs.index
        )
