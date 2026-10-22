# WikipediaAgent

A [Pydantic AI](https://ai.pydantic.dev/) agent that answers questions using only
English Wikipedia. It searches for the right page, reads it (in chunks for long
articles), and returns a structured answer that cites the pages it actually read.

```
$ uv run wiki-agent "Where do capybaras live?"
Capybaras are native to all countries in South America except Chile. ...

Sources:
- Capybara: https://en.wikipedia.org/wiki/Capybara
```

Design notes: [`CONTEXT.md`](CONTEXT.md) and
[ADR-0001](docs/adr/0001-wikipedia-agent-design.md).

## Setup

Requires [uv](https://docs.astral.sh/uv/) and Python 3.13.

```
uv sync
```

Create a `.env` file in the project root:

```
OPENAI_API_KEY=sk-...
# Optional: any Pydantic AI model name; defaults to openai:gpt-4o-mini
WIKI_AGENT_MODEL=openai:gpt-4o-mini
```

## CLI

```
uv run wiki-agent "Where do capybaras live?"   # answer once
uv run wiki-agent                              # interactive chat; type stop or exit to quit
uv run wiki-agent --verbose "..."              # also print each tool call and its arguments
```

The chat keeps the conversation history, so follow-ups like "and what do they
eat?" work, and it prints the total token usage when you quit. Ask in any
language: the agent searches English Wikipedia and replies in your language.

## Python / notebook

```python
from wiki_agent import create_agent, print_messages

agent = create_agent()
result = await agent.run("Where do capybaras live?")
result.output            # WikiAnswer(answer=..., sources=[Source(...)], found=True)
print_messages(result.all_messages())
```

`Agent Notebook.ipynb` walks through a question, its tool calls, a follow-up with
`message_history`, and `RunUsage`. Every run is capped by a default usage limit
so a looping model is stopped.

## Tests

```
uv run pytest            # offline: fake HTTP session and scripted model, no network or LLM
uv run pytest -m live    # opt-in smoke tests against real Wikipedia and the real model (needs .env)
```
