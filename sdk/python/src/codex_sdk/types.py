from __future__ import annotations

import json
from typing import Any, List, Literal, Set, TypedDict, Union

from typing_extensions import NotRequired

from .exceptions import ParseError


class UserTextInput(TypedDict):
    type: Literal["text"]
    text: str


class UserLocalImageInput(TypedDict):
    type: Literal["local_image"]
    path: str


UserInput = Union[UserTextInput, UserLocalImageInput]


class ThreadStartedEvent(TypedDict):
    type: Literal["thread.started"]
    thread_id: str


class TurnStartedEvent(TypedDict):
    type: Literal["turn.started"]


class Usage(TypedDict):
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int


class TurnCompletedEvent(TypedDict):
    type: Literal["turn.completed"]
    usage: Usage


class ThreadError(TypedDict):
    message: str


class TurnFailedEvent(TypedDict):
    type: Literal["turn.failed"]
    error: ThreadError


class AgentMessageItem(TypedDict):
    id: str
    type: Literal["agent_message"]
    text: str


class ReasoningItem(TypedDict):
    id: str
    type: Literal["reasoning"]
    text: str


CommandExecutionStatus = Literal["in_progress", "completed", "failed", "declined"]


class CommandExecutionItem(TypedDict):
    id: str
    type: Literal["command_execution"]
    command: str
    aggregated_output: str
    exit_code: NotRequired[int]
    status: CommandExecutionStatus


PatchChangeKind = Literal["add", "delete", "update"]


class FileUpdateChange(TypedDict):
    path: str
    kind: PatchChangeKind


PatchApplyStatus = Literal["in_progress", "completed", "failed"]


class FileChangeItem(TypedDict):
    id: str
    type: Literal["file_change"]
    changes: List[FileUpdateChange]
    status: PatchApplyStatus


McpToolCallStatus = Literal["in_progress", "completed", "failed"]


class McpToolCallResult(TypedDict, total=False):
    content: List[Any]
    structured_content: Any


class McpToolCallError(TypedDict):
    message: str


class McpToolCallItem(TypedDict):
    id: str
    type: Literal["mcp_tool_call"]
    server: str
    tool: str
    arguments: Any
    result: NotRequired[McpToolCallResult]
    error: NotRequired[McpToolCallError]
    status: McpToolCallStatus


class WebSearchItem(TypedDict):
    id: str
    type: Literal["web_search"]
    query: str


class TodoItem(TypedDict):
    text: str
    completed: bool


class TodoListItem(TypedDict):
    id: str
    type: Literal["todo_list"]
    items: List[TodoItem]


class ErrorItem(TypedDict):
    id: str
    type: Literal["error"]
    message: str


ThreadItem = Union[
    AgentMessageItem,
    ReasoningItem,
    CommandExecutionItem,
    FileChangeItem,
    McpToolCallItem,
    WebSearchItem,
    TodoListItem,
    ErrorItem,
]


class ItemCompletedEvent(TypedDict):
    type: Literal["item.completed"]
    item: ThreadItem


class ItemStartedEvent(TypedDict):
    type: Literal["item.started"]
    item: ThreadItem


class ItemUpdatedEvent(TypedDict):
    type: Literal["item.updated"]
    item: ThreadItem


class ThreadErrorEvent(TypedDict):
    type: Literal["error"]
    message: str


ThreadEvent = Union[
    ThreadStartedEvent,
    TurnStartedEvent,
    TurnCompletedEvent,
    TurnFailedEvent,
    ItemStartedEvent,
    ItemUpdatedEvent,
    ItemCompletedEvent,
    ThreadErrorEvent,
]

_EVENT_TYPES: Set[str] = {
    "thread.started",
    "turn.started",
    "turn.completed",
    "turn.failed",
    "item.started",
    "item.updated",
    "item.completed",
    "error",
}


def parse_thread_event(line: str) -> ThreadEvent:
    try:
        parsed = json.loads(line)
    except json.JSONDecodeError as e:
        raise ParseError(f"Failed to parse JSONL event: {line}") from e

    if not isinstance(parsed, dict):
        raise ParseError(f"Invalid event (expected object): {parsed!r}")

    event_type = parsed.get("type")
    if not isinstance(event_type, str):
        raise ParseError(f"Invalid event (missing type): {parsed!r}")
    if event_type not in _EVENT_TYPES:
        raise ParseError(f"Unknown event type {event_type!r}: {parsed!r}")

    if event_type in {"item.started", "item.updated", "item.completed"}:
        item = parsed.get("item")
        if not isinstance(item, dict):
            raise ParseError(f"Invalid {event_type} event (missing item): {parsed!r}")
        item_type = item.get("type")
        if not isinstance(item_type, str):
            raise ParseError(
                f"Invalid {event_type} event (missing item.type): {parsed!r}"
            )

    return parsed  # type: ignore[return-value]
