"""The example site that serves the test vocabularies."""

from pathlib import Path

import responses

EXAMPLE_VOCABULARIES = "https://example.test/vocabularies"
EXAMPLE_FILES = Path(__file__).parent / "test_fields" / "vocabularies"


def publish(
    web: responses.RequestsMock,
    name: str,
    body: bytes | Exception | None = None,
    etag: str = '"one"',
    status: int = 200,
    base: str = EXAMPLE_VOCABULARIES,
) -> None:
    """Have the example site answer the next request for a vocabulary file.

    Answers queue up: each request gets the next one, and the last repeats. A server
    that asks to be checked again at once is the one that serves the vocabularies.

    Args:
        web: The stand-in for the web.
        name: The file, without ``.ttl``.
        body: What the server sends, a file of the same name in the test vocabularies
            when not given. An exception is raised instead, as a lost connection.
        etag: The ``ETag`` header.
        status: The status code. A 304 carries no body.
        base: The address the file is published under.
    """
    if body is None and status == 200:
        body = (EXAMPLE_FILES / f"{name}.ttl").read_bytes()
    web.get(
        f"{base}/{name}.ttl",
        body=b"" if status == 304 else body,
        status=status,
        headers={"ETag": etag, "Cache-Control": "max-age=0"},
    )
