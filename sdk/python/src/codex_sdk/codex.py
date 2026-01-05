from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ._exec import CodexExec
from .options import CodexOptions, ThreadOptions
from .thread import Thread


@dataclass
class Codex:
    """
    Codex is the main entrypoint for interacting with the Codex agent.

    Use `start_thread()` to create a new conversation or `resume_thread()` to continue
    an existing one.
    """

    _exec: CodexExec
    _options: CodexOptions

    def __init__(self, options: Optional[CodexOptions] = None) -> None:
        self._options = options or CodexOptions()
        self._exec = CodexExec(
            codex_path_override=self._options.codex_path_override,
            env=self._options.env,
        )

    def start_thread(self, options: Optional[ThreadOptions] = None) -> Thread:
        return Thread(self._exec, self._options, options or ThreadOptions())

    def resume_thread(
        self, thread_id: str, options: Optional[ThreadOptions] = None
    ) -> Thread:
        return Thread(
            self._exec, self._options, options or ThreadOptions(), thread_id=thread_id
        )
