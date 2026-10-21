from fakes import search_response, wiki

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
