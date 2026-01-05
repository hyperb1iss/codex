import os
import unittest
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional

from codex_sdk import (
    CancelToken,
    CodexOptions,
    ThreadOptions,
    TurnOptions,
)
from codex_sdk.exceptions import ParseError
from codex_sdk.thread import Thread
from codex_sdk.types import parse_thread_event


@dataclass
class FakeExec:
    lines: List[str]
    last_kwargs: Optional[Dict[str, Any]] = None

    def run(self, **kwargs: Any) -> Iterator[str]:
        self.last_kwargs = dict(kwargs)
        for line in self.lines:
            yield line

    async def run_async(self, **kwargs: Any) -> AsyncIterator[str]:
        self.last_kwargs = dict(kwargs)
        for line in self.lines:
            yield line


class CodexSdkParsingTests(unittest.TestCase):
    def test_parse_thread_event_rejects_unknown_type(self) -> None:
        with self.assertRaises(ParseError):
            parse_thread_event('{"type":"nope"}')


class CodexSdkThreadTests(unittest.TestCase):
    def test_run_aggregates_final_response_items_and_usage(self) -> None:
        fake = FakeExec(
            lines=[
                '{"type":"thread.started","thread_id":"t1"}',
                '{"type":"turn.started"}',
                '{"type":"item.completed","item":{"id":"i1","type":"agent_message","text":"Hi!"}}',
                '{"type":"turn.completed","usage":{"input_tokens":1,"cached_input_tokens":0,"output_tokens":2}}',
            ]
        )
        thread = Thread(fake, CodexOptions(), ThreadOptions())
        turn = thread.run("hello")

        self.assertEqual(thread.id, "t1")
        self.assertEqual(turn.final_response, "Hi!")
        self.assertEqual(
            turn.items, [{"id": "i1", "type": "agent_message", "text": "Hi!"}]
        )
        self.assertEqual(
            turn.usage,
            {"input_tokens": 1, "cached_input_tokens": 0, "output_tokens": 2},
        )

    def test_structured_input_combines_text_and_forwards_images(self) -> None:
        fake = FakeExec(
            lines=[
                '{"type":"thread.started","thread_id":"t1"}',
                '{"type":"turn.completed","usage":{"input_tokens":0,"cached_input_tokens":0,"output_tokens":0}}',
            ]
        )
        thread = Thread(fake, CodexOptions(), ThreadOptions())
        thread.run(
            [
                {"type": "text", "text": "Line 1"},
                {"type": "text", "text": "Line 2"},
                {"type": "local_image", "path": "/tmp/a.png"},
            ]
        )

        last_kwargs = fake.last_kwargs
        if last_kwargs is None:
            raise AssertionError("expected exec kwargs")
        self.assertEqual(last_kwargs["input_text"], "Line 1\n\nLine 2")
        self.assertEqual(last_kwargs["images"], ["/tmp/a.png"])

    def test_output_schema_file_is_cleaned_up(self) -> None:
        observed_schema_path: Optional[str] = None

        class ExecCheckingSchema(FakeExec):
            def run(self, **kwargs: Any) -> Iterator[str]:
                nonlocal observed_schema_path
                observed_schema_path = kwargs.get("output_schema_file")
                if observed_schema_path is None:
                    raise AssertionError("expected output_schema_file")
                if not os.path.exists(observed_schema_path):
                    raise AssertionError("expected output_schema_file to exist")
                return super().run(**kwargs)

        fake = ExecCheckingSchema(
            lines=[
                '{"type":"thread.started","thread_id":"t1"}',
                '{"type":"turn.completed","usage":{"input_tokens":0,"cached_input_tokens":0,"output_tokens":0}}',
            ]
        )
        thread = Thread(fake, CodexOptions(), ThreadOptions())
        thread.run("structured", TurnOptions(output_schema={"type": "object"}))

        if observed_schema_path is None:
            raise AssertionError("expected output_schema_file")
        self.assertFalse(os.path.exists(observed_schema_path))  # cleaned after run

    def test_resume_thread_forwards_thread_id(self) -> None:
        fake = FakeExec(
            lines=[
                '{"type":"turn.completed","usage":{"input_tokens":0,"cached_input_tokens":0,"output_tokens":0}}',
            ]
        )
        thread = Thread(fake, CodexOptions(), ThreadOptions(), thread_id="t-resume")
        thread.run("next")
        last_kwargs = fake.last_kwargs
        if last_kwargs is None:
            raise AssertionError("expected exec kwargs")
        self.assertEqual(last_kwargs["thread_id"], "t-resume")

    def test_cancel_token_is_forwarded(self) -> None:
        fake = FakeExec(
            lines=[
                '{"type":"turn.completed","usage":{"input_tokens":0,"cached_input_tokens":0,"output_tokens":0}}',
            ]
        )
        token = CancelToken()
        thread = Thread(fake, CodexOptions(), ThreadOptions())
        thread.run("ok", TurnOptions(cancel_token=token))
        last_kwargs = fake.last_kwargs
        if last_kwargs is None:
            raise AssertionError("expected exec kwargs")
        self.assertIs(last_kwargs["cancel_token"], token)


class CodexSdkAsyncThreadTests(unittest.IsolatedAsyncioTestCase):
    async def test_run_async_works(self) -> None:
        fake = FakeExec(
            lines=[
                '{"type":"thread.started","thread_id":"t1"}',
                '{"type":"item.completed","item":{"id":"i1","type":"agent_message","text":"Hi!"}}',
                '{"type":"turn.completed","usage":{"input_tokens":1,"cached_input_tokens":0,"output_tokens":2}}',
            ]
        )
        thread = Thread(fake, CodexOptions(), ThreadOptions())
        turn = await thread.run_async("hello")
        self.assertEqual(turn.final_response, "Hi!")
