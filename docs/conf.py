"""Sphinx configuration for the ghfdb documentation."""

from importlib.metadata import version as _version

project = "ghfdb"
author = "International Heat Flow Commission"
copyright = "2026, International Heat Flow Commission"
release = _version("ghfdb")
version = release

extensions = ["myst_parser"]
source_suffix = {".md": "markdown"}
# docs/agents/ is guidance for automated contributors, not part of the site.
exclude_patterns = ["_build", "agents"]

html_theme = "furo"
html_title = "ghfdb"
html_static_path = ["_static"]
