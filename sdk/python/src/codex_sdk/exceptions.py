from __future__ import annotations

from typing import Optional


class CodexSdkError(Exception):
    pass


class CodexNotFoundError(CodexSdkError):
    pass


class CodexExecError(CodexSdkError):
    def __init__(
        self, exit_code: int, stderr: str, *, stdout_tail: Optional[str] = None
    ) -> None:
        message = f"codex exec exited with code {exit_code}"
        if stdout_tail:
            message += f"\n\nstdout (tail):\n{stdout_tail}"
        if stderr:
            message += f"\n\nstderr:\n{stderr}"
        super().__init__(message)
        self.exit_code = exit_code
        self.stderr = stderr
        self.stdout_tail = stdout_tail


class TurnFailedError(CodexSdkError):
    pass


class ParseError(CodexSdkError):
    pass


class CodexTimeoutError(CodexSdkError):
    def __init__(self, timeout_s: float) -> None:
        super().__init__(f"codex exec exceeded timeout ({timeout_s}s)")
        self.timeout_s = timeout_s


class CodexCancelledError(CodexSdkError):
    pass
