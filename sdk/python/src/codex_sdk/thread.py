from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import AsyncIterator, Iterator, List, Optional, Protocol, Tuple, Union

from ._schema_file import create_output_schema_file
from .cancellation import CancelToken
from .exceptions import TurnFailedError
from .options import CodexOptions, ThreadOptions, TurnOptions
from .types import ThreadEvent, ThreadItem, Usage, UserInput, parse_thread_event

Input = Union[str, List[UserInput]]


class ExecLike(Protocol):
    def run(
        self,
        *,
        input_text: str,
        base_url: Optional[str],
        api_key: Optional[str],
        thread_id: Optional[str],
        images: List[str],
        model: Optional[str],
        sandbox_mode: Optional[str],
        working_directory: Optional[str],
        additional_directories: Optional[List[str]],
        skip_git_repo_check: bool,
        output_schema_file: Optional[str],
        model_reasoning_effort: Optional[str],
        network_access_enabled: Optional[bool],
        web_search_enabled: Optional[bool],
        approval_policy: Optional[str],
        timeout_s: Optional[float],
        cancel_token: Optional[CancelToken],
    ) -> Iterator[str]: ...

    def run_async(
        self,
        *,
        input_text: str,
        base_url: Optional[str],
        api_key: Optional[str],
        thread_id: Optional[str],
        images: List[str],
        model: Optional[str],
        sandbox_mode: Optional[str],
        working_directory: Optional[str],
        additional_directories: Optional[List[str]],
        skip_git_repo_check: bool,
        output_schema_file: Optional[str],
        model_reasoning_effort: Optional[str],
        network_access_enabled: Optional[bool],
        web_search_enabled: Optional[bool],
        approval_policy: Optional[str],
        timeout_s: Optional[float],
        cancel_token: Optional[CancelToken],
    ) -> AsyncIterator[str]: ...


@dataclass(frozen=True)
class Turn:
    items: List[ThreadItem]
    final_response: str
    usage: Optional[Usage]


@dataclass(frozen=True)
class StreamedTurn:
    events: Iterator[ThreadEvent]


@dataclass(frozen=True)
class AsyncStreamedTurn:
    events: AsyncIterator[ThreadEvent]


class Thread:
    def __init__(
        self,
        exec_: ExecLike,
        codex_options: CodexOptions,
        thread_options: ThreadOptions,
        *,
        thread_id: Optional[str] = None,
    ) -> None:
        self._exec = exec_
        self._codex_options = codex_options
        self._thread_options = thread_options
        self._id: Optional[str] = thread_id

    @property
    def id(self) -> Optional[str]:
        return self._id

    def run_streamed(
        self, input_: Input, options: Optional[TurnOptions] = None
    ) -> StreamedTurn:
        return StreamedTurn(
            events=self._run_streamed_internal(input_, options or TurnOptions())
        )

    def run_streamed_async(
        self, input_: Input, options: Optional[TurnOptions] = None
    ) -> AsyncStreamedTurn:
        return AsyncStreamedTurn(
            events=self._run_streamed_internal_async(input_, options or TurnOptions())
        )

    def run(self, input_: Input, options: Optional[TurnOptions] = None) -> Turn:
        items: List[ThreadItem] = []
        final_response = ""
        usage: Optional[Usage] = None
        turn_failure: Optional[str] = None

        for event in self._run_streamed_internal(input_, options or TurnOptions()):
            if event["type"] == "thread.started":
                self._id = event["thread_id"]
            elif event["type"] == "item.completed":
                item = event["item"]
                if item["type"] == "agent_message":
                    final_response = item["text"]
                items.append(item)
            elif event["type"] == "turn.completed":
                usage = event["usage"]
            elif event["type"] == "turn.failed":
                turn_failure = event["error"]["message"]
                break
            elif event["type"] == "error":
                turn_failure = event["message"]
                break

        if turn_failure:
            raise TurnFailedError(turn_failure)
        return Turn(items=items, final_response=final_response, usage=usage)

    async def run_async(
        self, input_: Input, options: Optional[TurnOptions] = None
    ) -> Turn:
        items: List[ThreadItem] = []
        final_response = ""
        usage: Optional[Usage] = None
        turn_failure: Optional[str] = None

        async for event in self._run_streamed_internal_async(
            input_, options or TurnOptions()
        ):
            if event["type"] == "thread.started":
                self._id = event["thread_id"]
            elif event["type"] == "item.completed":
                item = event["item"]
                if item["type"] == "agent_message":
                    final_response = item["text"]
                items.append(item)
            elif event["type"] == "turn.completed":
                usage = event["usage"]
            elif event["type"] == "turn.failed":
                turn_failure = event["error"]["message"]
                break
            elif event["type"] == "error":
                turn_failure = event["message"]
                break

        if turn_failure:
            raise TurnFailedError(turn_failure)
        return Turn(items=items, final_response=final_response, usage=usage)

    def _run_streamed_internal(
        self, input_: Input, options: TurnOptions
    ) -> Iterator[ThreadEvent]:
        prompt, images = _normalize_input(input_)
        schema_path, cleanup = create_output_schema_file(options.output_schema)
        try:
            for line in self._exec.run(
                input_text=prompt,
                base_url=self._codex_options.base_url,
                api_key=self._codex_options.api_key,
                thread_id=self._id,
                images=images,
                model=self._thread_options.model,
                sandbox_mode=self._thread_options.sandbox_mode,
                working_directory=self._thread_options.working_directory,
                additional_directories=self._thread_options.additional_directories,
                skip_git_repo_check=self._thread_options.skip_git_repo_check,
                output_schema_file=schema_path,
                model_reasoning_effort=self._thread_options.model_reasoning_effort,
                network_access_enabled=self._thread_options.network_access_enabled,
                web_search_enabled=self._thread_options.web_search_enabled,
                approval_policy=self._thread_options.approval_policy,
                timeout_s=options.timeout_s,
                cancel_token=options.cancel_token,
            ):
                event = parse_thread_event(line)
                if event["type"] == "thread.started":
                    self._id = event["thread_id"]
                yield event
        finally:
            cleanup()

    async def _run_streamed_internal_async(
        self, input_: Input, options: TurnOptions
    ) -> AsyncIterator[ThreadEvent]:
        prompt, images = _normalize_input(input_)
        schema_path, cleanup = create_output_schema_file(options.output_schema)
        try:
            async for line in self._exec.run_async(
                input_text=prompt,
                base_url=self._codex_options.base_url,
                api_key=self._codex_options.api_key,
                thread_id=self._id,
                images=images,
                model=self._thread_options.model,
                sandbox_mode=self._thread_options.sandbox_mode,
                working_directory=self._thread_options.working_directory,
                additional_directories=self._thread_options.additional_directories,
                skip_git_repo_check=self._thread_options.skip_git_repo_check,
                output_schema_file=schema_path,
                model_reasoning_effort=self._thread_options.model_reasoning_effort,
                network_access_enabled=self._thread_options.network_access_enabled,
                web_search_enabled=self._thread_options.web_search_enabled,
                approval_policy=self._thread_options.approval_policy,
                timeout_s=options.timeout_s,
                cancel_token=options.cancel_token,
            ):
                event = parse_thread_event(line)
                if event["type"] == "thread.started":
                    self._id = event["thread_id"]
                yield event
        finally:
            await asyncio.to_thread(cleanup)


def _normalize_input(input_: Input) -> Tuple[str, List[str]]:
    if isinstance(input_, str):
        return input_, []

    prompt_parts: List[str] = []
    images: List[str] = []
    for item in input_:
        if item["type"] == "text":
            prompt_parts.append(item["text"])
        elif item["type"] == "local_image":
            images.append(item["path"])
        else:
            raise TypeError(f"Unknown input type: {item!r}")

    return "\n\n".join(prompt_parts), images
