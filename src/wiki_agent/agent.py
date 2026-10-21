"""Build the Wikipedia agent."""

import os

from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.models import Model

from wiki_agent.models import WikiAnswer
from wiki_agent.tools import WikipediaTools

DEFAULT_MODEL = "openai:gpt-4o-mini"

INSTRUCTIONS = """\
You answer questions using English Wikipedia.
First use `search` to find the exact page title, then `get_page` to read it.
"""


def create_agent(model: Model | str | None = None, tools: WikipediaTools | None = None) -> Agent[None, WikiAnswer]:
    """Create the agent; `model` defaults to `WIKI_AGENT_MODEL` (from `.env`), else gpt-4o-mini."""
    load_dotenv()
    tools = tools or WikipediaTools()
    return Agent(
        model or os.getenv("WIKI_AGENT_MODEL") or DEFAULT_MODEL,
        name="wikipedia",
        instructions=INSTRUCTIONS,
        tools=[tools.search, tools.get_page],
        output_type=WikiAnswer,
        defer_model_check=True,
    )
