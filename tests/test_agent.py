import pytest
from fakes import search_response, wiki
from scripted import answer, call, scripted, tool_returns

from pydantic_ai.exceptions import UsageLimitExceeded

from wiki_agent.agent import create_agent
from wiki_agent.models import Source, WikiAnswer
from wiki_agent.tools import WikipediaTools

CAPYBARA = "The '''capybara''' is a giant rodent native to South America."


def capybara_tools() -> WikipediaTools:
    return WikipediaTools(
        session=wiki(
            search={"capybara habitat": search_response(("Capybara", "giant rodent"))},
            pages={"Capybara": CAPYBARA},
        )
    )


def test_default_model_comes_from_wiki_agent_model(monkeypatch):
    monkeypatch.setenv("WIKI_AGENT_MODEL", "openai:gpt-4.1")

    assert create_agent().model == "openai:gpt-4.1"


def test_default_model_falls_back_to_gpt_4o_mini(monkeypatch):
    monkeypatch.delenv("WIKI_AGENT_MODEL", raising=False)

    assert create_agent().model == "openai:gpt-4o-mini"


def test_agent_searches_reads_page_and_answers_citing_it():
    seen = {}

    def final(messages, info):
        seen["page"] = tool_returns(messages, "get_page")
        return answer(answer="South America.", sources=[{"title": "Capybara"}], found=True)(messages, info)

    model = scripted(
        call("search", query="capybara habitat"),
        call("get_page", title="Capybara"),
        final,
    )
    agent = create_agent(model=model, tools=capybara_tools())

    result = agent.run_sync("Where do capybaras live?")

    assert seen["page"] == [CAPYBARA]
    assert result.output == WikiAnswer(
        answer="South America.",
        sources=[Source(title="Capybara")],
        found=True,
    )
    assert result.output.sources[0].url == "https://en.wikipedia.org/wiki/Capybara"


def test_source_url_uses_underscored_title():
    assert Source(title="Rio de Janeiro").url == "https://en.wikipedia.org/wiki/Rio_de_Janeiro"


def test_agent_recovers_from_missing_page_by_searching_again():
    seen = {}

    def final(messages, info):
        seen["pages"] = tool_returns(messages, "get_page")
        return answer(answer="South America.", sources=[{"title": "Capybara"}], found=True)(messages, info)

    model = scripted(
        call("get_page", title="Capybarra"),
        call("search", query="capybara habitat"),
        call("get_page", title="Capybara"),
        final,
    )
    agent = create_agent(model=model, tools=capybara_tools())

    result = agent.run_sync("Where do capybaras live?")

    assert seen["pages"][0].startswith("Page 'Capybarra' was not found.")
    assert seen["pages"][1] == CAPYBARA
    assert result.output.found is True


def test_looping_model_is_stopped_by_default_usage_limit():
    session = wiki(search={"capybara": search_response(("Capybara", "giant rodent"))})
    agent = create_agent(model=scripted(call("search", query="capybara")), tools=WikipediaTools(session=session))

    with pytest.raises(UsageLimitExceeded):
        agent.run_sync("Where do capybaras live?")

    assert len(session.calls) <= 8  # budget: ~3 searches + ~3 page reads, a little slack


def test_not_found_answer_round_trips_with_empty_sources():
    model = scripted(
        call("search", query="capybara habitat"),
        answer(answer="Wikipedia doesn't say.", sources=[], found=False),
    )
    agent = create_agent(model=model, tools=capybara_tools())

    result = agent.run_sync("What is the capybara's favourite song?")

    assert result.output == WikiAnswer(answer="Wikipedia doesn't say.", sources=[], found=False)


def test_source_url_is_always_built_from_title():
    source = Source.model_validate({"title": "Capybara", "url": "https://example.com/made-up"})

    assert source.url == "https://en.wikipedia.org/wiki/Capybara"
