"""Smoke tests against real Wikipedia and the real model. Run with `uv run pytest -m live`."""

import pytest
from pydantic_ai.messages import ToolCallPart

from wiki_agent import WikipediaTools, create_agent

pytestmark = pytest.mark.live


def titles(answer) -> list[str]:
    return [source.title for source in answer.sources]


def test_capybara_question_is_found_and_cites_capybara():
    result = create_agent().run_sync("Where do capybaras live?")

    assert result.output.found is True
    assert "Capybara" in titles(result.output)


def test_content_deep_in_an_article_is_reached_by_paging():
    agent = create_agent(tools=WikipediaTools(chunk_size=2000))

    result = agent.run_sync(
        "According to the Wikipedia article on the capybara, why could its meat be eaten during Lent in Venezuela?"
    )

    offsets = [
        part.args_as_dict().get("offset", 0)
        for message in result.all_messages()
        for part in message.parts
        if isinstance(part, ToolCallPart) and part.tool_name == "get_page"
    ]
    assert max(offsets, default=0) > 0
    assert result.output.found is True
    assert "Capybara" in titles(result.output)


def test_non_english_question_gets_reply_in_that_language_citing_english_pages():
    result = create_agent().run_sync("¿Dónde viven los capibaras?")

    assert result.output.found is True
    assert "américa" in result.output.answer.lower()  # Spanish spelling; English would be "America"
    assert "Capybara" in titles(result.output)
    assert all(source.url.startswith("https://en.wikipedia.org/wiki/") for source in result.output.sources)
