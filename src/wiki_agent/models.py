"""Structured output of the agent: a WikiAnswer citing its Sources."""

from urllib.parse import quote

from pydantic import BaseModel, Field, computed_field


class Source(BaseModel):
    """A Wikipedia page the agent actually read with `get_page`."""

    title: str = Field(description="Exact title of a page read with get_page.")

    @computed_field
    @property
    def url(self) -> str:
        """Always built from the title, so the model can't cite a made-up link."""
        return "https://en.wikipedia.org/wiki/" + quote(self.title.replace(" ", "_"), safe="/:_,()'")


class WikiAnswer(BaseModel):
    """The agent's answer, grounded in the Wikipedia pages it read."""

    answer: str = Field(
        description="The answer, written in the language of the user's question (not necessarily English)."
    )
    sources: list[Source] = Field(default_factory=list, description="Only pages read with get_page.")
    found: bool = Field(description="False when the pages read do not contain the answer.")
