"""The ``ghfdb`` command."""

import argparse
import sys
from pathlib import Path

import pandas

from ghfdb.dataset import Dataset
from ghfdb.fields import MissingSchemeError, Vocabularies, load_schema
from ghfdb.qc.report import Report
from ghfdb.qc.rules import RULES
from ghfdb.qc.workbook import CheckError, UploadWorkbook

DOWNLOAD_ADVICE = (
    "The vocabularies must be downloaded once, with a network connection, "
    "before a workbook can be checked."
)


def check(path: Path) -> int:
    """Check a workbook and write its report.

    Args:
        path: The workbook.

    Returns:
        0 when no problem was found, 1 when there are problems.

    Raises:
        CheckError: The workbook cannot be checked or the report cannot be written.
        MissingSchemeError: A vocabulary a field names is not defined where it is
            published.
        OSError: The vocabularies are not cached and cannot be downloaded.
    """
    vocabularies = Vocabularies()
    try:
        schema = load_schema(vocabularies=vocabularies)
    except OSError as error:
        raise OSError(f"{error} {DOWNLOAD_ADVICE}") from error
    workbook = UploadWorkbook(path, schema)
    dataset = Dataset(workbook.data())
    problems = pandas.concat(
        [workbook.column_problems(), dataset.check(schema, RULES, vocabularies)]
    )
    children = len(dataset.data)
    report = Report(path, problems, children, vocabularies).write()
    affected = problems["row"].dropna().nunique()
    print(
        f"{children} children, {len(problems)} problems in {affected} of them, "
        f"report: {report}"
    )
    return 1 if len(problems) else 0


def main(argv: list[str] | None = None) -> int:
    """Run the command.

    Args:
        argv: The arguments after the command name. Without them, those the command
            was run with.

    Returns:
        The exit status: 0 when no problem was found, 1 when problems were found and
        2 when the check could not be run, with the reason on standard error.
    """
    parser = argparse.ArgumentParser(prog="ghfdb")
    commands = parser.add_subparsers(dest="command", required=True)
    checking = commands.add_parser(
        "check", help="check a filled-in upload template workbook"
    )
    checking.add_argument("workbook", type=Path, help="the .xlsx or .xlsm workbook")
    arguments = parser.parse_args(argv)
    try:
        return check(arguments.workbook)
    except (CheckError, MissingSchemeError, OSError) as error:
        print(error, file=sys.stderr)
        return 2


def run() -> None:
    """Run the command and exit with its status."""
    sys.exit(main())
