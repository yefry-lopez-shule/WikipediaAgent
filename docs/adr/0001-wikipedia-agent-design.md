# ADR-0001: Wikipedia Agent design

- Status: Accepted
- Date: 2026-10-20

## Context

Build a Pydantic AI agent that answers questions from Wikipedia using the Search
API and the raw Get Page API (User-Agent header required). Starting point: the
draft in `scrips_ref/potencial tools.txt` and the course notebook
`scrips_ref/pydantic-ai.ipynb`.

## Decisions

1. **Shape** — importable package `src/wiki_agent/` plus a demo notebook
   (`Agent Notebook.ipynb`) that imports it. Remove `package = false`; entry
   point `wiki-agent = "wiki_agent.cli:main"`; add `requests` (dep) and
   `pytest` (dev).
2. **Tools** — a `WikipediaTools` class (course `SearchTools` pattern) with an
   injected `requests.Session`, `lang="en"`, `search_limit=5`,
   `chunk_size=8000`. Methods `search` and `get_page` are registered as tools.
3. **Long pages** — light regex cleanup of wikitext (refs, comments, simple
   templates), then paging: `get_page(title, offset=0)` returns one chunk plus
   a `[truncated: showing a–b of N chars; call again with offset=b]` note.
4. **Errors** — 404 returns a message telling the model to search for the
   exact title; `#REDIRECT [[X]]` is followed one level; network/HTTP errors
   raise `ModelRetry`; requests use a ~10s timeout. No backoff retries.
5. **Output** — `output_type=WikiAnswer(answer, sources: list[Source], found)`,
   `Source(title, url)`.
6. **Grounding** — always search first (optionally one reformulated search),
   read 1–2 best pages (more chunks only if needed), answer only from what was
   read, cite only pages actually read, `found=False` when not answerable.
   Budget ≈3 searches / 3 page reads, enforced with `UsageLimits(request_limit=…)`.
7. **Model** — `create_agent(model=None)`; reads `WIKI_AGENT_MODEL` from `.env`
   (python-dotenv), default `openai:gpt-4o-mini`.
8. **Language** — English instructions/docstrings, English search queries,
   reply in the user's language. `lang` kept configurable for later.
9. **Testing** — pytest: `WikipediaTools` unit tests with a fake session (no
   network); agent wiring tests with Pydantic AI `TestModel` (no LLM); optional
   `@pytest.mark.live` tests skipped by default. Built test-first.
10. **CLI** — `wiki-agent "question"` answers once; no argument starts a chat
    loop with `message_history`, `stop`/`exit` to quit, cumulative `RunUsage`
    printed at the end; `--verbose` prints tool calls via `print_messages`.

## Consequences

- Tools are testable offline; the agent is model-agnostic via config.
- Paging keeps context small but may cost extra tool calls on deep questions.
- Section-level retrieval (a third tool) and non-English editions are deferred.

## Implementation notes

- `Agent` takes no default `usage_limits`, so a `WikiAgent` subclass defaults
  them in `iter()` (which `run`, `run_sync` and `run_stream` all go through).
  The default is `request_limit=12`: 8 cut off legitimate runs that page
  through a long article. Callers can pass `usage_limits=` to override it.
- Agent wiring tests use a scripted `FunctionModel` rather than `TestModel`, so
  each test controls the exact tool-call sequence.
- `create_agent` also accepts `tools=` so tests can inject a fake session.
- `Source.url` is computed from the title; the model cannot supply it.
