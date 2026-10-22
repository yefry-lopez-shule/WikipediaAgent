import pytest
import requests
from fakes import FakeResponse, FakeSession, search_response, wiki
from pydantic_ai import ModelRetry

from wiki_agent.tools import WikipediaTools


def test_search_hits_search_api_with_query_and_user_agent():
    session = wiki(search={"capybara": search_response(("Capybara", "The <span class=\"searchmatch\">capybara</span> is a rodent"))})
    tools = WikipediaTools(session=session)

    results = tools.search("capybara")

    assert results == [{"title": "Capybara", "snippet": "The capybara is a rodent"}]
    [call] = session.calls
    assert call.url == "https://en.wikipedia.org/w/api.php"
    assert call.params["list"] == "search"
    assert call.params["srsearch"] == "capybara"
    assert call.params["srlimit"] == 5
    assert "User-Agent" in call.headers


def test_get_page_hits_raw_api_for_exact_title_and_returns_at_most_one_chunk():
    session = wiki(pages={"Capybara": "x" * 50})
    tools = WikipediaTools(session=session, chunk_size=20)

    page = tools.get_page("Capybara")

    assert page.startswith("x" * 20)
    assert "x" * 21 not in page
    [call] = session.calls
    assert call.url == "https://en.wikipedia.org/w/index.php"
    assert call.params == {"title": "Capybara", "action": "raw"}


def test_get_page_returns_cleaned_text_without_refs_comments_or_simple_templates():
    wikitext = (
        "{{Short description|Giant rodent}}\n"
        "The capybara<ref name=\"a\">{{cite web|url=http://x}}</ref> is a rodent<ref name=\"b\" /> "
        "<!-- hidden\nnote --> of [[South America]].{{citation needed|date=May 2020}}\n"
        "{{Infobox animal\n| range = South America\n}}"
    )
    tools = WikipediaTools(session=wiki(pages={"Capybara": wikitext}))

    page = tools.get_page("Capybara")

    assert page == (
        "The capybara is a rodent of [[South America]].\n"
        "{{Infobox animal\n| range = South America\n}}"
    )


LONG_PAGE = "0123456789" * 5  # 50 chars


def test_long_page_returns_one_chunk_with_truncation_note():
    tools = WikipediaTools(session=wiki(pages={"Long": LONG_PAGE}), chunk_size=20)

    page = tools.get_page("Long")

    assert page == "01234567890123456789\n\n[truncated: showing 0–20 of 50 chars; call again with offset=20]"


def test_paging_with_offset_returns_next_chunks_and_last_has_no_note():
    tools = WikipediaTools(session=wiki(pages={"Long": LONG_PAGE}), chunk_size=20)

    middle = tools.get_page("Long", offset=20)
    last = tools.get_page("Long", offset=40)

    assert middle == "01234567890123456789\n\n[truncated: showing 20–40 of 50 chars; call again with offset=40]"
    assert last == "0123456789"


def test_offset_past_end_returns_clear_message():
    tools = WikipediaTools(session=wiki(pages={"Long": LONG_PAGE}), chunk_size=20)

    message = tools.get_page("Long", offset=50)

    assert message == "Offset 50 is past the end of 'Long' (50 chars). Use a smaller offset."


def test_redirect_is_followed_and_identifies_target_title():
    session = wiki(pages={"Capybaras": "#REDIRECT [[Capybara]]\n{{R from plural}}", "Capybara": "A giant rodent."})
    tools = WikipediaTools(session=session)

    page = tools.get_page("Capybaras")

    assert page == "[Redirected from 'Capybaras' to 'Capybara']\n\nA giant rodent."
    assert [c.params["title"] for c in session.calls] == ["Capybaras", "Capybara"]


def test_redirect_chain_stops_after_one_hop():
    session = wiki(pages={"A": "#REDIRECT [[B]]", "B": "#REDIRECT [[C]]", "C": "Final."})
    tools = WikipediaTools(session=session)

    page = tools.get_page("A")

    assert page == "[Redirected from 'A' to 'B']\n\n#REDIRECT [[C]]"
    assert [c.params["title"] for c in session.calls] == ["A", "B"]


def test_missing_page_returns_not_found_message():
    tools = WikipediaTools(session=wiki())

    message = tools.get_page("Capybarra")

    assert message == "Page 'Capybarra' was not found. Use search to find the exact title, then call get_page with it."


def failing(error: Exception | None = None, status: int = 200):
    def responder(url, params):
        if error:
            raise error
        return FakeResponse(status_code=status)

    return FakeSession(responder)


@pytest.mark.parametrize(
    "session",
    [
        failing(requests.Timeout("timed out")),
        failing(requests.ConnectionError("no route")),
        failing(status=503),
    ],
    ids=["timeout", "connection-error", "5xx"],
)
@pytest.mark.parametrize("use_tool", [lambda t: t.search("capybara"), lambda t: t.get_page("Capybara")], ids=["search", "get_page"])
def test_network_and_server_errors_raise_model_retry(session, use_tool):
    with pytest.raises(ModelRetry, match="Wikipedia"):
        use_tool(WikipediaTools(session=session))


def test_requests_are_sent_with_a_timeout():
    session = wiki(search={"capybara": search_response(("Capybara", ""))}, pages={"Capybara": "Rodent."})
    tools = WikipediaTools(session=session)

    tools.search("capybara")
    tools.get_page("Capybara")

    assert [c.timeout for c in session.calls] == [10, 10]


def test_malformed_search_response_raises_model_retry():
    tools = WikipediaTools(session=FakeSession(lambda url, params: FakeResponse(json_data={"error": "bad"})))

    with pytest.raises(ModelRetry, match="Wikipedia"):
        tools.search("capybara")


def test_negative_offset_returns_clear_message():
    tools = WikipediaTools(session=wiki(pages={"Long": LONG_PAGE}), chunk_size=20)

    assert tools.get_page("Long", offset=-5) == "Offset -5 is negative. Use offset=0 to read 'Long' from the start."
