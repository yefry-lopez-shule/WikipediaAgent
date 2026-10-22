"""Wikipedia tools the agent calls: search for titles, then read pages."""

import re
from typing import Any, Protocol

import requests
from pydantic_ai import ModelRetry

USER_AGENT = "wiki-agent/0.1 (educational project; https://github.com/yefry-lopez-shule/WikipediaAgent)"
HEADERS = {"User-Agent": USER_AGENT}
TIMEOUT = 10  # seconds


_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_REF = re.compile(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", re.DOTALL | re.IGNORECASE)
_SIMPLE_TEMPLATE = re.compile(r"\{\{[^{}\n]*\}\}")
_REDIRECT = re.compile(r"\s*#REDIRECT\s*\[\[([^\]|#]+)", re.IGNORECASE)


def clean_wikitext(wikitext: str) -> str:
    """Remove refs, HTML comments and simple (single-line) templates; keep infoboxes."""
    text = _COMMENT.sub("", wikitext)
    text = _REF.sub("", text)
    while (stripped := _SIMPLE_TEMPLATE.sub("", text)) != text:
        text = stripped
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _not_found(title: str) -> str:
    return f"Page '{title}' was not found. Use search to find the exact title, then call get_page with it."


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
        response = self._get("api.php", params)
        try:
            hits = response.json()["query"]["search"]
        except (ValueError, KeyError, TypeError) as error:
            raise ModelRetry(f"Wikipedia returned an unexpected search response ({error!r}). Try again.") from error
        return [{"title": hit["title"], "snippet": re.sub(r"<[^>]+>", "", hit["snippet"])} for hit in hits]

    def get_page(self, title: str, offset: int = 0) -> str:
        """Get the cleaned text of a Wikipedia page by its exact title, one chunk at a time.

        Use this after `search`, with a title it returned. Long pages are returned in
        chunks: if the text ends with a `[truncated: ...; call again with offset=N]` note
        and you need more of the page, call again with that `offset`.

        Args:
            title: Exact page title, e.g. "Quantum computing".
            offset: Character position to start reading from; 0 for the beginning.
        """
        wikitext = self._fetch_raw(title)
        prefix = ""
        if wikitext is not None and (redirect := _REDIRECT.match(wikitext)):
            target = redirect.group(1).strip()
            prefix = f"[Redirected from '{title}' to '{target}']\n\n"
            title, wikitext = target, self._fetch_raw(target)
        if wikitext is None:
            return prefix + _not_found(title)
        return prefix + self._chunk(title, clean_wikitext(wikitext), offset)

    def _fetch_raw(self, title: str) -> str | None:
        """Raw wikitext of `title`, or None if the page does not exist."""
        params = {"title": title, "action": "raw"}
        response = self._get("index.php", params, allow_404=True)
        return None if response.status_code == 404 else response.text

    def _get(self, path: str, params: dict[str, Any], allow_404: bool = False) -> HttpResponse:
        """GET a Wikipedia endpoint; failures become ModelRetry so the model can try again."""
        try:
            response = self.session.get(f"{self.base_url}/{path}", params=params, headers=HEADERS, timeout=TIMEOUT)
            if not (allow_404 and response.status_code == 404):
                response.raise_for_status()
        except requests.RequestException as error:
            raise ModelRetry(f"Wikipedia request failed ({error}). Try again or try a different query.") from error
        return response

    def _chunk(self, title: str, text: str, offset: int) -> str:
        total = len(text)
        if offset < 0:
            return f"Offset {offset} is negative. Use offset=0 to read '{title}' from the start."
        if offset >= total and offset > 0:
            return f"Offset {offset} is past the end of '{title}' ({total} chars). Use a smaller offset."
        end = offset + self.chunk_size
        chunk = text[offset:end]
        if end < total:
            chunk += f"\n\n[truncated: showing {offset}–{end} of {total} chars; call again with offset={end}]"
        return chunk
