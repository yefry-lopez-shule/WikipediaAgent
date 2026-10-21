# Wikipedia Agent — Context

A Pydantic AI agent that answers questions using only English Wikipedia, via two
endpoints: the Search API (`api.php?action=query&list=search`) and the Get Page
API (`index.php?action=raw`). See [ADR-0001](docs/adr/0001-wikipedia-agent-design.md).

## Glossary

- **Search result** — one hit from the Search API: `title` + `snippet` (HTML stripped).
  Used to discover the exact page title. Never cited as a source on its own.
- **Page** — the raw wikitext of one Wikipedia article, fetched by exact title.
- **Cleaned text** — page wikitext after light cleanup (refs, HTML comments,
  simple templates removed).
- **Chunk** — a fixed-size slice of cleaned text, addressed by `offset`. A
  truncated chunk ends with a note telling the model the next `offset`.
- **Redirect** — a page whose wikitext is `#REDIRECT [[Target]]`; followed
  automatically one level deep.
- **WikiAnswer** — the agent's structured output: `answer`, `sources`, `found`.
- **Source** — a page the agent actually read with `get_page`: `title` + `url`
  (`https://en.wikipedia.org/wiki/<Title>`).
- **Grounded** — the answer uses only facts from pages read in this run. If the
  pages don't contain the answer, `found=False` rather than guessing.

## Components

- `WikipediaTools` (`src/wiki_agent/tools.py`) — holds the HTTP session
  (User-Agent set), `lang`, search limit, chunk size. Methods `search(query)`
  and `get_page(title, offset=0)` are the agent's tools.
- `create_agent(model=None)` (`src/wiki_agent/agent.py`) — builds the agent;
  model from `WIKI_AGENT_MODEL`, default `openai:gpt-4o-mini`.
- `main` (`src/wiki_agent/cli.py`) — one-shot answer or interactive chat loop.
