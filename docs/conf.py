"""Sphinx configuration for the ghfdb documentation."""

import sys
from importlib.metadata import version as _version
from pathlib import Path
from typing import Any

from sphinx.application import Sphinx

sys.path.insert(0, str(Path(__file__).parent))

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
    "extensions.field_reference",
    "extensions.upload_template",
]
source_suffix = {".md": "markdown"}
# docs/agents/ is guidance for automated contributors, and ROADMAP.md is read on GitHub;
# neither is part of the site.
exclude_patterns = ["_build", "agents", "ROADMAP.md"]

html_theme = "furo"
html_title = "ghfdb"
html_static_path = ["_static"]

# Mermaid is loaded as one classic script with a subresource integrity hash, so the
# browser refuses a changed file from the CDN. sphinxcontrib-mermaid's own loader is an
# inline module that imports the library, and an import cannot carry a hash. It is
# pointed at a shim that re-exports the global the hashed script defines. To upgrade
# mermaid, change the version and the hash together:
#   curl -sL https://cdn.jsdelivr.net/npm/mermaid@<version>/dist/mermaid.min.js \
#     | openssl dgst -sha384 -binary | openssl base64 -A
MERMAID_VERSION = "11.12.1"
MERMAID_INTEGRITY = (
    "sha384-LlKSgo4Eo5GuF/ZrstLti44dE+GC5XAJ7TSu0Nw9Q3vIZF2QMnkRcK7BUoLabYLF"
)
mermaid_use_local = "mermaid-global.mjs"


def add_mermaid_script(
    app: Sphinx,
    pagename: str,
    templatename: str,
    context: dict[str, Any],
    doctree: Any,
) -> None:
    """Load the hashed mermaid script wherever the extension loads its module.

    The extension skips only the pages that have a doctree and no diagram.
    """
    if doctree and not next(doctree.findall(lambda n: n.tagname == "mermaid"), None):
        return
    app.add_js_file(
        f"https://cdn.jsdelivr.net/npm/mermaid@{MERMAID_VERSION}/dist/mermaid.min.js",
        integrity=MERMAID_INTEGRITY,
        crossorigin="anonymous",
    )


def setup(app: Sphinx) -> None:
    app.connect("html-page-context", add_mermaid_script)
