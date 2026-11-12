import subprocess
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
    def test_exports_the_public_names(self) -> None:
        from ghfdb.fields import (  # noqa: F401
            allowed_values,
            field_for_column,
            load_schema,
        )
        from ghfdb.vocabularies import (  # noqa: F401
            AllowedValue,
            MissingSchemeError,
            Vocabularies,
            caching_session,
        )


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

    def test_contains_no_vocabulary_files(self, wheel_names: set[str]) -> None:
        assert {name for name in wheel_names if name.endswith(".ttl")} == set()

    def test_contains_nothing_from_the_repository_outside_the_package(
        self, wheel_names: set[str]
    ) -> None:
        stray = {
            name for name in wheel_names if not name.startswith(("ghfdb/", "ghfdb-"))
        }

        assert stray == set()
