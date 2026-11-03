from importlib.metadata import version

import ghfdb
import ghfdb.qc


class TestPackage:
    def test_version_matches_the_installed_distribution(self) -> None:
        assert ghfdb.__version__ == version("ghfdb")

    def test_qc_subpackage_imports(self) -> None:
        assert ghfdb.qc.__name__ == "ghfdb.qc"
