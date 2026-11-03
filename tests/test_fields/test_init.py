import subprocess
import sys


class TestPublicSurface:
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
