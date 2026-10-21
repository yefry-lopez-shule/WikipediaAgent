"""Script a `FunctionModel` turn by turn so agent runs need no LLM."""

from typing import Any, Callable

from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

Respond = Callable[[list[ModelMessage], AgentInfo], ModelResponse]
Step = ModelResponse | Respond


def scripted(*steps: Step) -> FunctionModel:
    """Each model request consumes the next step; the last step repeats forever."""
    remaining = list(steps)

    def fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        step = remaining.pop(0) if len(remaining) > 1 else remaining[0]
        return step(messages, info) if callable(step) else step

    return FunctionModel(fn)


def call(tool: str, **args: Any) -> ModelResponse:
    return ModelResponse(parts=[ToolCallPart(tool, args)])


def answer(**output: Any) -> Respond:
    return lambda messages, info: ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, output)])


def tool_returns(messages: list[ModelMessage], tool: str) -> list[Any]:
    return [
        part.content
        for message in messages
        for part in message.parts
        if isinstance(part, ToolReturnPart) and part.tool_name == tool
    ]
