"""Command line entry point: `wiki-agent "question"`."""

import argparse
import os

from wiki_agent.agent import create_agent
from wiki_agent.models import WikiAnswer


def print_answer(answer: WikiAnswer) -> None:
    print(answer.answer)
    if answer.sources:
        print("\nSources:")
        for source in answer.sources:
            print(f"- {source.title}: {source.url}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="wiki-agent", description="Answer questions from Wikipedia.")
    parser.add_argument("question", help="The question to answer.")
    args = parser.parse_args(argv)
    os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

    result = create_agent().run_sync(args.question)
    print_answer(result.output)
