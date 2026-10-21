"""Structured output of the agent: a WikiAnswer citing its Sources."""

from urllib.parse import quote

from pydantic import BaseModel, Field, model_validator


class Source(BaseModel):
    """A Wikipedia page the agent actually read with `get_page`."""

    title: str = Field(description="Exact title of a page read with get_page.")
    url: str = Field(default="", description="Leave empty; filled in from the title.")

    @model_validator(mode="after")
    def _fill_url(self) -> "Source":
        if not self.url:
            self.url = "https://en.wikipedia.org/wiki/" + quote(self.title.replace(" ", "_"), safe="/:_,()'")
        return self


class WikiAnswer(BaseModel):
    """The agent's answer, grounded in the Wikipedia pages it read."""

    answer: str = Field(description="The answer, in the user's language.")
    sources: list[Source] = Field(default_factory=list, description="Only pages read with get_page.")
    found: bool = Field(description="False when the pages read do not contain the answer.")
