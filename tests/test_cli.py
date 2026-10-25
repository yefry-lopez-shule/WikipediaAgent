from fakes import search_response, wiki
from scripted import answer, call, scripted

from pydantic_ai.messages import ModelRequest, UserPromptPart

from wiki_agent import cli
from wiki_agent.agent import create_agent
from wiki_agent.tools import WikipediaTools

CAPYBARA = "The '''capybara''' is a giant rodent native to South America."


def capybara_tools() -> WikipediaTools:
    return WikipediaTools(
        session=wiki(
            search={"capybara": search_response(("Capybara", "giant rodent"))},
            pages={"Capybara": CAPYBARA},
        )
    )


def typing(monkeypatch, *lines: str) -> None:
    remaining = list(lines)
    monkeypatch.setattr("builtins.input", lambda prompt="": remaining.pop(0))


def user_prompts(messages) -> list[str]:
    return [
        part.content
        for message in messages
        if isinstance(message, ModelRequest)
        for part in message.parts
        if isinstance(part, UserPromptPart)
    ]


def test_chat_passes_earlier_turns_to_follow_ups(monkeypatch, capsys):
    seen = []

    def final(messages, info):
        seen.append(user_prompts(messages))
        return answer(answer="Grass.", sources=[{"title": "Capybara"}], found=True)(messages, info)

    agent = create_agent(model=scripted(final), tools=capybara_tools())
    typing(monkeypatch, "What is a capybara?", "and what do they eat?", "stop")

    cli.chat(agent, verbose=False)

    assert seen == [
        ["What is a capybara?"],
        ["What is a capybara?", "and what do they eat?"],
    ]
    assert "Total usage:" in capsys.readouterr().out


def test_chat_quits_on_exit_and_skips_blank_lines(monkeypatch, capsys):
    agent = create_agent(model=scripted(answer(answer="Hi.", sources=[], found=False)), tools=capybara_tools())
    typing(monkeypatch, "", "EXIT")

    cli.chat(agent, verbose=False)

    out = capsys.readouterr().out
    assert "Hi." not in out
    assert "Total usage:" in out


def test_chat_ends_cleanly_on_eof(monkeypatch, capsys):
    agent = create_agent(model=scripted(answer(answer="Hi.", sources=[], found=False)), tools=capybara_tools())

    def eof(prompt=""):
        raise EOFError

    monkeypatch.setattr("builtins.input", eof)

    cli.chat(agent, verbose=False)

    assert "Total usage:" in capsys.readouterr().out


def verbose_agent():
    model = scripted(
        call("search", query="capybara"),
        answer(answer="A giant rodent.", sources=[{"title": "Capybara"}], found=True),
    )
    return create_agent(model=model, tools=capybara_tools())


def test_verbose_one_shot_prints_tool_calls_with_args(capsys):
    assert cli.ask_once(verbose_agent(), "What is a capybara?", verbose=True) == 0

    out = capsys.readouterr().out
    assert "TOOL CALL: search {'query': 'capybara'}" in out
    assert "TOOL RETURN: search" in out
    assert "Sources:\n- Capybara: https://en.wikipedia.org/wiki/Capybara" in out


def test_verbose_chat_prints_tool_calls_with_args(monkeypatch, capsys):
    typing(monkeypatch, "What is a capybara?", "stop")

    cli.chat(verbose_agent(), verbose=True)

    assert "TOOL CALL: search {'query': 'capybara'}" in capsys.readouterr().out


def test_quiet_one_shot_hides_tool_calls(capsys):
    cli.ask_once(verbose_agent(), "What is a capybara?", verbose=False)

    out = capsys.readouterr().out
    assert "TOOL CALL" not in out
    assert "A giant rodent." in out


def test_print_messages_is_exported_from_package():
    from wiki_agent import print_messages
    from wiki_agent.display import print_messages as original

    assert print_messages is original
