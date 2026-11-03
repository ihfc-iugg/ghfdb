import subprocess
import sys
from importlib.metadata import version

import ghfdb
import ghfdb.qc


class TestPackage:
    def test_version_matches_the_installed_distribution(self) -> None:
        assert ghfdb.__version__ == version("ghfdb")

    def test_qc_subpackage_imports(self) -> None:
        assert ghfdb.qc.__name__ == "ghfdb.qc"


class TestFieldsPublicSurface:
    def test_exports_the_public_names_without_importing_rdflib(self) -> None:
        code = (
            "import sys\n"
            "from ghfdb.fields import (FieldSchema, Field, AllowedValue,\n"
            "    VocabularyBinding, VocabularyRelease, UnknownFieldError)\n"
            "assert 'rdflib' not in sys.modules\n"
        )

        result = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, check=False
        )

        assert result.returncode == 0, result.stderr
