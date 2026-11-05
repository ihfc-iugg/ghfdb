"""Python tools for working with the Global Heat Flow Database."""

from importlib.metadata import version

__version__ = version("ghfdb")

from ghfdb.dataset import Dataset  # noqa: E402

__all__ = ["Dataset", "__version__"]
