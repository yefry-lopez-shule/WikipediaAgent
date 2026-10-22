"""Print an agent run's messages: prompts, tool calls with args, tool returns, text."""

from collections.abc import Sequence

from pydantic_ai.messages import ModelMessage


def print_messages(messages: Sequence[ModelMessage]) -> None:
    for message in messages:
        for part in message.parts:
            match part.part_kind:
                case "user-prompt":
                    print("USER:", part.content)
                case "tool-call":
                    print("TOOL CALL:", part.tool_name, part.args)
                case "tool-return":
                    print("TOOL RETURN:", part.tool_name, f"({len(str(part.content))} chars)")
                case "retry-prompt":
                    print("RETRY:", part.tool_name, part.content)
                case "text":
                    print(part.content)
