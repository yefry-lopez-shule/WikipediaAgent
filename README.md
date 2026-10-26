# WikipediaAgent

A question-answering agent that uses **only English Wikipedia** as its source.
Ask it a question in any language. It searches Wikipedia, reads the relevant
pages and answers in your language, citing the pages it read. If those pages
don't contain the answer, it says so instead of guessing.

It's built with [Pydantic AI](https://ai.pydantic.dev/) and uses OpenAI's
`gpt-4o-mini` by default. You can switch to any model Pydantic AI supports.

```
$ uv run wiki-agent "Where do capybaras live?"
Capybaras are native to all countries in South America except Chile. They live
near rivers, lakes, swamps and other freshwater, in savannas, wetlands and
forests, mostly in lowlands ...

Sources:
- Capybara: https://en.wikipedia.org/wiki/Capybara
```

## Contents

- [What it does](#what-it-does)
- [How it works](#how-it-works)
- [Setup](#setup)
- [Usage](#usage): [CLI](#command-line), [Python](#python), [Notebook](#notebook)
- [Configuration](#configuration)
- [Project structure](#project-structure)
- [Tests](#tests)
- [Troubleshooting](#troubleshooting)

## What it does

- **Grounded answers.** The agent answers only from Wikipedia text it read
  during the current run, not from the model's own memory or from search
  snippets.
- **Real citations.** `sources` lists only pages the agent actually opened.
  Each URL is built from the page title, so the model can't invent a link.
- **Honest "not found".** When the pages don't answer the question, the agent
  sets `found=False` and tells you.
- **Any language.** It searches English Wikipedia but answers in the language
  you asked in (Spanish in, Spanish out).
- **Long articles.** Pages are cleaned and read in 8,000-character chunks, so
  the agent can page through long articles without flooding its context.
- **Conversations.** Follow-up questions such as "and what do they eat?" work,
  in both the chat CLI and Python.
- **Built-in budget.** Each run is capped at 12 model requests, so a model
  that gets stuck in a loop is stopped.

## How it works

The agent has two tools, and its instructions tell it to use them in order:

```
 question
    │
    ▼
┌──────────┐   titles +    ┌────────────┐  page text   ┌──────────────┐
│  search  │──snippets────▶│  get_page  │─(chunked)───▶│  WikiAnswer  │
└──────────┘               └────────────┘              └──────────────┘
 Wikipedia Search API       raw wikitext, cleaned;      answer, sources,
 finds exact page titles    "[truncated: ... offset=N]" found
                            note means "read the next chunk"
```

1. **`search(query)`** calls the Wikipedia Search API and returns the top 5
   titles with snippets. It runs first, to find the exact page title.
2. **`get_page(title, offset=0)`** fetches the page's raw wikitext and strips
   references, HTML comments and simple templates. It returns one chunk. If
   more text remains, the chunk ends with a note giving the next `offset`.
   Redirects are followed automatically, and a missing page returns a hint to
   search again.
3. The model answers with a structured **`WikiAnswer`**:

   | Field     | Type           | Meaning                                       |
   |-----------|----------------|-----------------------------------------------|
   | `answer`  | `str`          | The answer, in the language of the question   |
   | `sources` | `list[Source]` | Pages read with `get_page` (`title`, `url`)   |
   | `found`   | `bool`         | `False` if the pages didn't contain the answer|

If Wikipedia is unreachable or returns an error, the tool raises `ModelRetry`,
so the model sees the error and can try again.

Design decisions are recorded in [ADR-0001](docs/adr/0001-wikipedia-agent-design.md),
and the vocabulary (chunk, source, grounded, ...) in [`CONTEXT.md`](CONTEXT.md).

## Setup

You need [uv](https://docs.astral.sh/uv/), Python 3.13 (uv can install it for
you) and an OpenAI API key.

```bash
git clone https://github.com/yefry-lopez-shule/WikipediaAgent.git
cd WikipediaAgent
uv sync
```

Create a `.env` file in the project root (it's git-ignored):

```
OPENAI_API_KEY=sk-...
# Optional: any Pydantic AI model name (default: openai:gpt-4o-mini)
WIKI_AGENT_MODEL=openai:gpt-4o-mini
```

## Usage

### Command line

```bash
uv run wiki-agent "Where do capybaras live?"      # ask one question
uv run wiki-agent                                 # interactive chat
uv run wiki-agent --verbose "Who built Machu Picchu?"  # also show each tool call
```

In chat mode the agent remembers the conversation, so you can ask follow-ups.
Type `stop` or `exit` (or press Ctrl+C) to quit. Total token usage is printed
when you leave.

`--verbose` (`-v`) prints every step, so you can see which tools the agent used:

```
USER: Where do capybaras live?
TOOL CALL: search {"query":"capybara habitat"}
TOOL RETURN: search (998 chars)
TOOL CALL: get_page {"title":"Capybara"}
TOOL RETURN: get_page (8073 chars)
TOOL CALL: final_result {"answer":"Capybaras are native to ...","found":true}
```

`final_result` is not a Wikipedia tool. It's how Pydantic AI returns the
structured `WikiAnswer`.

### Python

```python
from wiki_agent import create_agent, print_messages

agent = create_agent()

result = agent.run_sync("Where do capybaras live?")   # or: await agent.run(...)
print(result.output.answer)
for source in result.output.sources:
    print(source.title, source.url)

# See which tools were called
print_messages(result.new_messages())

# Follow-up question: pass the history
followup = agent.run_sync("And what do they eat?", message_history=result.all_messages())

# Tokens, requests and tool calls for a run
print(result.usage)
```

More options:

```python
from pydantic_ai.usage import UsageLimits
from wiki_agent import WikipediaTools, create_agent

# Another model (any Pydantic AI model string)
agent = create_agent(model="openai:gpt-4.1")

# Tune the tools: more search results, smaller chunks
agent = create_agent(tools=WikipediaTools(search_limit=10, chunk_size=4000))

# Override the per-run budget (default: 12 model requests)
agent.run_sync("...", usage_limits=UsageLimits(request_limit=20))

# Call the tools directly, without an LLM
wiki = WikipediaTools()
wiki.search("capybara")
wiki.get_page("Capybara", offset=8000)
```

### Notebook

[`Agent Notebook.ipynb`](Agent%20Notebook.ipynb) is a guided tour:

1. Calling the tools directly, without an LLM
2. Asking a question and reading the `WikiAnswer`
3. Checking which tools the agent used (`print_messages`, tool names, usage)
4. Watching tool calls live with `agent.iter`
5. Asking a follow-up question with `message_history`
6. Asking in Spanish
7. An unanswerable question (`found=False`)
8. Adding up usage, and hitting a usage limit on purpose

To run it, open the notebook in VS Code or Jupyter and **select the project's
`.venv` as the kernel**. A full run makes about 20 cheap `gpt-4o-mini`
requests (around $0.01).

## Configuration

| Setting                | Where                      | Default              |
|------------------------|----------------------------|----------------------|
| `OPENAI_API_KEY`       | `.env`                     | required for OpenAI  |
| `WIKI_AGENT_MODEL`     | `.env`                     | `openai:gpt-4o-mini` |
| `model=`               | `create_agent()`           | `WIKI_AGENT_MODEL`   |
| `search_limit`         | `WikipediaTools()`         | `5` results          |
| `chunk_size`           | `WikipediaTools()`         | `8000` characters    |
| `usage_limits=`        | `agent.run()` / `run_sync()` | 12 requests        |

To use another provider, set `WIKI_AGENT_MODEL` (for example
`anthropic:claude-sonnet-5-5`), add that provider's API key to `.env`, and
install its Pydantic AI extra if needed.

## Project structure

```
WikipediaAgent/
├── src/wiki_agent/
│   ├── agent.py      # create_agent(), instructions, usage budget
│   ├── tools.py      # WikipediaTools: search() and get_page(), wikitext cleanup, chunking
│   ├── models.py     # WikiAnswer and Source (structured output)
│   ├── display.py    # print_messages(): shows prompts and tool calls
│   └── cli.py        # the `wiki-agent` command
├── tests/            # offline unit tests + opt-in live tests
├── docs/adr/         # architecture decision records
├── Agent Notebook.ipynb
├── CONTEXT.md        # glossary and components
└── pyproject.toml
```

## Tests

```bash
uv run pytest           # offline: fake HTTP session and scripted model, no network or API key
uv run pytest -m live   # opt-in: real Wikipedia + real model (needs .env, costs a few cents)
```

The offline suite covers the tools (search, chunking, redirects, errors), the
agent wiring and the CLI. The live tests check a real answer end to end, paging
deep into a long article, and a non-English question.

## Troubleshooting

- **`ModuleNotFoundError: No module named 'pydantic_ai'` in the notebook.**
  The kernel isn't the project's environment. Pick `.venv` in the kernel picker.
- **`UserError: Set the OPENAI_API_KEY environment variable ...`.** `.env` is missing
  or doesn't contain `OPENAI_API_KEY`. It must be in the project root.
- **`UsageLimitExceeded`.** The question needed more than 12 model requests.
  Pass a larger `usage_limits`, or ask a narrower question.
- **Answer has `found=False`.** The pages the agent read didn't contain the
  answer. Try rephrasing, or naming the subject more precisely.

## License

[GPL-3.0](LICENSE)
