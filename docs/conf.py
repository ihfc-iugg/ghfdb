"""Sphinx configuration for the ghfdb documentation."""

from importlib.metadata import version as _version

project = "ghfdb"
author = "International Heat Flow Commission"
copyright = "2026, International Heat Flow Commission"
release = _version("ghfdb")
version = release

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinxcontrib.mermaid",
]
source_suffix = {".md": "markdown"}
# docs/agents/ is guidance for automated contributors, and ROADMAP.md is read on GitHub;
# neither is part of the site.
exclude_patterns = ["_build", "agents", "ROADMAP.md"]

html_theme = "furo"
html_title = "ghfdb"
html_static_path = ["_static"]
