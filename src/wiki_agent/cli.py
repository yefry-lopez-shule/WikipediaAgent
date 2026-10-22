"""Command line entry point: `wiki-agent "question"` answers once; no argument starts a chat."""

import argparse
import os
import sys

from pydantic_ai import RunUsage
from pydantic_ai.exceptions import AgentRunError
from pydantic_ai.messages import ModelMessage

from wiki_agent.agent import WikiAgent, create_agent
from wiki_agent.display import print_messages
from wiki_agent.models import WikiAnswer

QUIT_WORDS = {"stop", "exit"}


def print_answer(answer: WikiAnswer) -> None:
    print(answer.answer)
    if answer.sources:
        print("\nSources:")
        for source in answer.sources:
            print(f"- {source.title}: {source.url}")


def ask_once(agent: WikiAgent, question: str, verbose: bool) -> int:
    try:
        result = agent.run_sync(question)
    except AgentRunError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    if verbose:
        print_messages(result.new_messages())
    print_answer(result.output)
    return 0


def chat(agent: WikiAgent, verbose: bool) -> None:
    messages: list[ModelMessage] = []
    usage = RunUsage()
    print("Ask anything; answers come from Wikipedia. Type 'stop' or 'exit' to quit.")
    while True:
        try:
            prompt = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if prompt.lower() in QUIT_WORDS:
            break
        if not prompt:
            continue
        try:
            result = agent.run_sync(prompt, message_history=messages)
        except AgentRunError as error:
            print(f"Error: {error}")
            continue
        usage = usage + result.usage
        if verbose:
            print_messages(result.new_messages())
        print()
        print_answer(result.output)
        messages = result.all_messages()
    print(f"\nTotal usage: {usage}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="wiki-agent", description="Answer questions from Wikipedia.")
    parser.add_argument("question", nargs="?", help="Answer this question once; omit to start a chat.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print tool calls and returns.")
    args = parser.parse_args(argv)
    os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

    agent = create_agent()
    if args.question:
        sys.exit(ask_once(agent, args.question, args.verbose))
    chat(agent, args.verbose)
