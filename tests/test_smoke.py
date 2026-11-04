import subprocess
import sys
import zipfile
from importlib.metadata import version
from pathlib import Path

import pytest

import ghfdb
import ghfdb.qc

ROOT = Path(__file__).parents[1]


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


@pytest.fixture(scope="module")
def wheel_names(tmp_path_factory: pytest.TempPathFactory) -> set[str]:
    out_dir = tmp_path_factory.mktemp("wheel")
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(out_dir), str(ROOT)],
        check=True,
        capture_output=True,
    )
    (wheel,) = out_dir.glob("ghfdb-*.whl")
    with zipfile.ZipFile(wheel) as archive:
        return set(archive.namelist())


class TestBuiltWheel:
    def test_contains_the_package_modules(self, wheel_names: set[str]) -> None:
        expected = {
            "ghfdb/__init__.py",
            "ghfdb/template.py",
            "ghfdb/fields/__init__.py",
            "ghfdb/qc/__init__.py",
        }

        assert expected <= wheel_names

    def test_contains_the_field_schema(self, wheel_names: set[str]) -> None:
        assert "ghfdb/fields/schema.json" in wheel_names

    def test_contains_nothing_from_the_repository_outside_the_package(
        self, wheel_names: set[str]
    ) -> None:
        stray = {
            name for name in wheel_names if not name.startswith(("ghfdb/", "ghfdb-"))
        }

        assert stray == set()
