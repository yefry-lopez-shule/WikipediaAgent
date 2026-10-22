"""Build the Wikipedia agent."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.models import Model
from pydantic_ai.run import AgentRun
from pydantic_ai.usage import UsageLimits

from wiki_agent.models import WikiAnswer
from wiki_agent.tools import WikipediaTools

DEFAULT_MODEL = "openai:gpt-4o-mini"

# ~3 searches + ~3 page reads + the final answer, with one request of slack.
USAGE_LIMITS = UsageLimits(request_limit=8)

INSTRUCTIONS = """\
You answer questions using only English Wikipedia.

How to work:
1. Always start with `search`. Write search queries in English, even when the
   question is in another language. If the results don't fit, you may try one
   reformulated search.
2. Read the 1-2 most relevant pages with `get_page`, using exact titles from the
   search results. Only request more chunks (with `offset`) if the answer is not
   in what you've read so far.
3. Answer only from the text of pages you read with `get_page` in this
   conversation. Do not use outside knowledge, and do not answer from search
   snippets alone.

Your answer:
- Write `answer` in the same language as the user's question, translating from
  the English pages when needed: a question in Spanish gets an answer in
  Spanish, a question in French an answer in French, and so on.
- List in `sources` only pages you actually read with `get_page`; never cite a
  page you only saw in search results.
- If the pages you read don't contain the answer, set `found` to false and say
  so briefly instead of guessing.
"""


class WikiAgent(Agent[None, WikiAnswer]):
    """An `Agent` whose runs default to the Wikipedia usage budget (`USAGE_LIMITS`)."""

    @asynccontextmanager
    async def iter(  # type: ignore[override]
        self, *args: Any, usage_limits: UsageLimits | None = None, **kwargs: Any
    ) -> AsyncIterator[AgentRun[None, Any]]:
        async with super().iter(*args, usage_limits=usage_limits or USAGE_LIMITS, **kwargs) as run:
            yield run


def create_agent(model: Model | str | None = None, tools: WikipediaTools | None = None) -> WikiAgent:
    """Create the agent; `model` defaults to `WIKI_AGENT_MODEL` (from `.env`), else gpt-4o-mini."""
    load_dotenv()
    tools = tools or WikipediaTools()
    return WikiAgent(
        model or os.getenv("WIKI_AGENT_MODEL") or DEFAULT_MODEL,
        name="wikipedia",
        instructions=INSTRUCTIONS,
        tools=[tools.search, tools.get_page],
        output_type=WikiAnswer,
        deps_type=type(None),
        defer_model_check=True,
    )
