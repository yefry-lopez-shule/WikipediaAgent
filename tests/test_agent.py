from fakes import search_response, wiki
from scripted import answer, call, scripted, tool_returns

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
        sources=[Source(title="Capybara", url="https://en.wikipedia.org/wiki/Capybara")],
        found=True,
    )


def test_source_url_uses_underscored_title():
    assert Source(title="Rio de Janeiro").url == "https://en.wikipedia.org/wiki/Rio_de_Janeiro"
