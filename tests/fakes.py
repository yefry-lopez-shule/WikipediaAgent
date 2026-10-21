"""Offline stand-ins for `requests.Session` used by the tests."""

from dataclasses import dataclass, field
from typing import Any, Callable

import requests


@dataclass
class FakeResponse:
    status_code: int = 200
    text: str = ""
    json_data: Any = None

    def json(self) -> Any:
        return self.json_data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error", response=self)  # type: ignore[arg-type]


@dataclass
class Call:
    url: str
    params: dict[str, Any]
    headers: dict[str, str]
    timeout: Any


@dataclass
class FakeSession:
    """Answers GETs from a `responder(url, params) -> FakeResponse` and records each call."""

    responder: Callable[[str, dict[str, Any]], FakeResponse]
    calls: list[Call] = field(default_factory=list)

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        params = dict(kwargs.get("params") or {})
        self.calls.append(Call(url, params, dict(kwargs.get("headers") or {}), kwargs.get("timeout")))
        return self.responder(url, params)


def search_response(*hits: tuple[str, str]) -> FakeResponse:
    return FakeResponse(
        json_data={"query": {"search": [{"title": t, "snippet": s} for t, s in hits]}}
    )


def wiki(search: dict[str, FakeResponse] | None = None, pages: dict[str, str] | None = None) -> FakeSession:
    """A fake Wikipedia: `search` maps query -> response, `pages` maps title -> wikitext."""
    search = search or {}
    pages = pages or {}

    def responder(url: str, params: dict[str, Any]) -> FakeResponse:
        if url.endswith("/api.php"):
            return search.get(params["srsearch"], search_response())
        if params.get("title") in pages:
            return FakeResponse(text=pages[params["title"]])
        return FakeResponse(status_code=404, text="")

    return FakeSession(responder)
