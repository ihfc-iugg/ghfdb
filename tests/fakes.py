"""A fake web for the tests that read vocabulary files without the network."""

from collections.abc import Mapping
from io import BytesIO
from pathlib import Path

from requests import PreparedRequest, Response, Session
from requests.adapters import BaseAdapter
from requests_cache import CachedSession
from urllib3.response import HTTPResponse

FIXTURES = Path(__file__).parent / "test_fields" / "vocabularies"


class FakeSite(BaseAdapter):
    """A stand-in for the web that serves the test vocabularies.

    A request for ``<anything>/<name>.ttl`` is answered with ``<name>.ttl`` from the
    test vocabularies, or from ``override``, with an ``ETag`` and a ``Cache-Control``
    that asks to check again at once. A request carrying that ``ETag`` is answered
    with 304.
    """

    def __init__(self) -> None:
        super().__init__()
        self.requests: list[PreparedRequest] = []
        self.failure: Exception | None = None
        self.etag = '"one"'
        self.override: dict[str, bytes] = {}

    def send(
        self,
        request: PreparedRequest,
        stream: bool = False,
        timeout: float | tuple[float, float] | tuple[float, None] | None = None,
        verify: bool | str = True,
        cert: bytes | str | tuple[bytes | str, bytes | str] | None = None,
        proxies: Mapping[str, str] | None = None,
    ) -> Response:
        self.requests.append(request)
        if self.failure is not None:
            raise self.failure
        assert request.url is not None
        name = request.url.rsplit("/", 1)[-1]
        path = FIXTURES / name
        status, body = 200, b""
        if name in self.override:
            body = self.override[name]
        elif not path.is_file():
            status = 404
        elif request.headers.get("If-None-Match") == self.etag:
            status = 304
        else:
            body = path.read_bytes()
        headers = {"ETag": self.etag, "Cache-Control": "max-age=0"}
        response = Response()
        response.url = request.url
        response.request = request
        response.status_code = status
        response.headers.update(headers)
        response.raw = HTTPResponse(
            body=BytesIO(body),
            status=status,
            headers=headers,
            preload_content=False,
            request_url=request.url,
        )
        return response

    def close(self) -> None:
        pass


def fake_session(site: FakeSite) -> Session:
    """A caching session, kept in memory, that talks to a fake site."""
    session = CachedSession(
        backend="memory", cache_control=True, expire_after=0, stale_if_error=True
    )
    session.mount("https://", site)
    return session
