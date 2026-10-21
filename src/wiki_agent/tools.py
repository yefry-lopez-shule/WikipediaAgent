"""Wikipedia tools the agent calls: search for titles, then read pages."""

import re
from typing import Any, Protocol

import requests

USER_AGENT = "wiki-agent/0.1 (educational project; https://github.com/yefry-lopez-shule/WikipediaAgent)"
HEADERS = {"User-Agent": USER_AGENT}


class HttpResponse(Protocol):
    @property
    def status_code(self) -> int: ...
    @property
    def text(self) -> str: ...

    def json(self) -> Any: ...
    def raise_for_status(self) -> None: ...


class HttpSession(Protocol):
    """The slice of `requests.Session` the tools use."""

    def get(self, url: str, **kwargs: Any) -> HttpResponse: ...


class WikipediaTools:
    """Search and read English Wikipedia through an injected HTTP session."""

    def __init__(
        self,
        session: HttpSession | None = None,
        lang: str = "en",
        search_limit: int = 5,
        chunk_size: int = 8000,
    ) -> None:
        self.session: HttpSession = session or requests.Session()
        self.lang = lang
        self.search_limit = search_limit
        self.chunk_size = chunk_size

    @property
    def base_url(self) -> str:
        return f"https://{self.lang}.wikipedia.org/w"

    def search(self, query: str) -> list[dict[str, Any]]:
        """Search Wikipedia and return the title and snippet of the best matches.

        Use this first to find the exact title of the relevant page.

        Args:
            query: Search terms, in English.
        """
        params = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": query,
            "srlimit": self.search_limit,
        }
        response = self.session.get(f"{self.base_url}/api.php", params=params, headers=HEADERS)
        response.raise_for_status()
        return [
            {"title": hit["title"], "snippet": re.sub(r"<[^>]+>", "", hit["snippet"])}
            for hit in response.json()["query"]["search"]
        ]

    def get_page(self, title: str) -> str:
        """Get the content of a Wikipedia page by its exact title.

        Use this after `search`, with a title it returned.

        Args:
            title: Exact page title, e.g. "Quantum computing".
        """
        params = {"title": title, "action": "raw"}
        response = self.session.get(f"{self.base_url}/index.php", params=params, headers=HEADERS)
        response.raise_for_status()
        return response.text[: self.chunk_size]
