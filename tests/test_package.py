from importlib.metadata import version

import ghfdb
import ghfdb.qc


def test_version_matches_the_installed_distribution():
    assert ghfdb.__version__ == version("ghfdb")


def test_qc_subpackage_imports():
    assert ghfdb.qc.__name__ == "ghfdb.qc"
