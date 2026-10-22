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
