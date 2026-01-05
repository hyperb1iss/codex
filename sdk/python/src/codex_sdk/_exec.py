from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import threading
import time
from collections import deque
from dataclasses import dataclass
from queue import Empty, Queue
from typing import AsyncIterator, Deque, Dict, Iterator, List, Optional, Tuple

from .cancellation import CancelToken
from .exceptions import (
    CodexCancelledError,
    CodexExecError,
    CodexNotFoundError,
    CodexTimeoutError,
)

_INTERNAL_ORIGINATOR_ENV = "CODEX_INTERNAL_ORIGINATOR_OVERRIDE"
_PYTHON_SDK_ORIGINATOR = "codex_sdk_py"


@dataclass(frozen=True)
class CodexExec:
    codex_path_override: Optional[str] = None
    env: Optional[Dict[str, str]] = None

    def _resolve_executable(self) -> str:
        if self.codex_path_override:
            return self.codex_path_override
        resolved = shutil.which("codex")
        if not resolved:
            raise CodexNotFoundError(
                "Could not find `codex` on PATH. Install Codex CLI or pass codex_path_override."
            )
        return resolved

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
    ) -> Iterator[str]:
        exe = self._resolve_executable()
        args: List[str] = ["exec", "--experimental-json"]

        if model:
            args += ["--model", model]
        if sandbox_mode:
            args += ["--sandbox", sandbox_mode]
        if working_directory:
            args += ["--cd", working_directory]
        if additional_directories:
            for d in additional_directories:
                args += ["--add-dir", d]
        if skip_git_repo_check:
            args += ["--skip-git-repo-check"]
        if output_schema_file:
            args += ["--output-schema", output_schema_file]
        if model_reasoning_effort:
            args += ["--config", f'model_reasoning_effort="{model_reasoning_effort}"']
        if network_access_enabled is not None:
            args += [
                "--config",
                f"sandbox_workspace_write.network_access={str(network_access_enabled).lower()}",
            ]
        if web_search_enabled is not None:
            args += [
                "--config",
                f"features.web_search_request={str(web_search_enabled).lower()}",
            ]
        if approval_policy:
            args += ["--config", f'approval_policy="{approval_policy}"']
        for image in images:
            args += ["--image", image]
        if thread_id:
            args += ["resume", thread_id]
        args.append("-")

        env = _build_env(self.env, base_url=base_url, api_key=api_key)
        proc = subprocess.Popen(
            [exe, *args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            bufsize=1,
        )

        if proc.stdin is None or proc.stdout is None or proc.stderr is None:
            _terminate_proc(proc)
            raise RuntimeError("codex subprocess missing stdio handles")

        stdout_queue, stdout_sentinel, stderr_buf, threads = _start_reader_threads(proc)
        stdout_tail: Deque[str] = deque(maxlen=200)
        stream_exhausted = False
        try:
            try:
                proc.stdin.write(input_text)
            finally:
                proc.stdin.close()

            for line in _drain_stdout(
                stdout_queue,
                stdout_sentinel,
                timeout_s=timeout_s,
                cancel_token=cancel_token,
            ):
                stdout_tail.append(line)
                yield line

            stream_exhausted = True
            rc = proc.wait()
            for t in threads:
                t.join(timeout=0.5)

            stderr = "".join(stderr_buf)
            if rc != 0:
                raise CodexExecError(rc, stderr, stdout_tail="\n".join(stdout_tail))
        finally:
            if not stream_exhausted:
                _terminate_proc(proc)
            for t in threads:
                t.join(timeout=0.5)

    async def run_async(
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
    ) -> AsyncIterator[str]:
        exe = self._resolve_executable()
        args: List[str] = ["exec", "--experimental-json"]

        if model:
            args += ["--model", model]
        if sandbox_mode:
            args += ["--sandbox", sandbox_mode]
        if working_directory:
            args += ["--cd", working_directory]
        if additional_directories:
            for d in additional_directories:
                args += ["--add-dir", d]
        if skip_git_repo_check:
            args += ["--skip-git-repo-check"]
        if output_schema_file:
            args += ["--output-schema", output_schema_file]
        if model_reasoning_effort:
            args += ["--config", f'model_reasoning_effort="{model_reasoning_effort}"']
        if network_access_enabled is not None:
            args += [
                "--config",
                f"sandbox_workspace_write.network_access={str(network_access_enabled).lower()}",
            ]
        if web_search_enabled is not None:
            args += [
                "--config",
                f"features.web_search_request={str(web_search_enabled).lower()}",
            ]
        if approval_policy:
            args += ["--config", f'approval_policy="{approval_policy}"']
        for image in images:
            args += ["--image", image]
        if thread_id:
            args += ["resume", thread_id]
        args.append("-")

        env = _build_env(self.env, base_url=base_url, api_key=api_key)
        proc = await asyncio.create_subprocess_exec(
            exe,
            *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        assert proc.stdin is not None
        assert proc.stdout is not None
        assert proc.stderr is not None

        proc.stdin.write(input_text.encode("utf-8"))
        await proc.stdin.drain()
        proc.stdin.close()

        stderr_buf: Deque[str] = deque(maxlen=16_384)
        stdout_tail: Deque[str] = deque(maxlen=200)

        async def read_stderr() -> None:
            assert proc.stderr is not None
            async for raw in proc.stderr:
                stderr_buf.append(raw.decode("utf-8", errors="replace"))

        stderr_task = asyncio.create_task(read_stderr())
        stream_exhausted = False
        try:
            async for line in _drain_stdout_async(
                proc.stdout, timeout_s=timeout_s, cancel_token=cancel_token
            ):
                stdout_tail.append(line)
                yield line
            stream_exhausted = True
        finally:
            if not stream_exhausted:
                await _terminate_proc_async(proc)
                stderr_task.cancel()
                try:
                    await stderr_task
                except Exception:
                    pass

        rc = await proc.wait()
        await stderr_task
        stderr = "".join(stderr_buf)
        if rc != 0:
            raise CodexExecError(rc, stderr, stdout_tail="\n".join(stdout_tail))


def _build_env(
    override_env: Optional[Dict[str, str]],
    *,
    base_url: Optional[str],
    api_key: Optional[str],
) -> Dict[str, str]:
    env: Dict[str, str] = {}
    if override_env is not None:
        env.update(override_env)
    else:
        env.update(os.environ)

    env.setdefault(_INTERNAL_ORIGINATOR_ENV, _PYTHON_SDK_ORIGINATOR)
    if base_url:
        env["OPENAI_BASE_URL"] = base_url
    if api_key:
        env["CODEX_API_KEY"] = api_key
    return env


def _start_reader_threads(
    proc: subprocess.Popen[str],
) -> Tuple["Queue[object]", object, "Deque[str]", List[threading.Thread]]:
    stdout_queue: "Queue[object]" = Queue()
    stdout_sentinel = object()
    stderr_buf: "Deque[str]" = deque(maxlen=16_384)

    def read_stdout() -> None:
        assert proc.stdout is not None
        try:
            for raw in proc.stdout:
                stdout_queue.put(raw.rstrip("\n"))
        finally:
            stdout_queue.put(stdout_sentinel)

    def read_stderr() -> None:
        assert proc.stderr is not None
        for raw in proc.stderr:
            stderr_buf.append(raw)

    threads = [
        threading.Thread(target=read_stdout, name="codex-sdk-stdout", daemon=True),
        threading.Thread(target=read_stderr, name="codex-sdk-stderr", daemon=True),
    ]
    for t in threads:
        t.start()

    return stdout_queue, stdout_sentinel, stderr_buf, threads


def _drain_stdout(
    stdout_queue: "Queue[object]",
    stdout_sentinel: object,
    *,
    timeout_s: Optional[float],
    cancel_token: Optional[CancelToken],
) -> Iterator[str]:
    start = time.monotonic()
    while True:
        remaining: Optional[float]
        if timeout_s is None:
            remaining = None
        else:
            elapsed = time.monotonic() - start
            remaining = timeout_s - elapsed
            if remaining <= 0:
                raise CodexTimeoutError(timeout_s)

        poll_s: float
        if remaining is None:
            poll_s = 0.1
        else:
            poll_s = min(0.1, remaining)

        if cancel_token is not None and cancel_token.is_cancelled():
            raise CodexCancelledError("codex exec cancelled")

        try:
            item = stdout_queue.get(timeout=poll_s)
        except Empty:
            if cancel_token is not None and cancel_token.is_cancelled():
                raise CodexCancelledError("codex exec cancelled") from None
            if timeout_s is not None and (time.monotonic() - start) >= timeout_s:
                raise CodexTimeoutError(timeout_s) from None
            continue

        if item is stdout_sentinel:
            return
        if isinstance(item, str):
            yield item


def _terminate_proc(proc: subprocess.Popen[str]) -> None:
    try:
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=0.5)
    except Exception:
        pass

    try:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=0.5)
    except Exception:
        return


async def _drain_stdout_async(
    stream: asyncio.StreamReader,
    *,
    timeout_s: Optional[float],
    cancel_token: Optional[CancelToken],
) -> AsyncIterator[str]:
    start = time.monotonic()
    while True:
        if cancel_token is not None and cancel_token.is_cancelled():
            raise CodexCancelledError("codex exec cancelled")

        remaining: Optional[float]
        if timeout_s is None:
            remaining = None
        else:
            remaining = timeout_s - (time.monotonic() - start)
            if remaining <= 0:
                raise CodexTimeoutError(timeout_s)

        poll_s = 0.1 if remaining is None else min(0.1, remaining)
        try:
            raw = await asyncio.wait_for(stream.readline(), timeout=poll_s)
        except asyncio.TimeoutError:
            continue

        if raw == b"":
            return
        yield raw.decode("utf-8", errors="replace").rstrip("\n")


async def _terminate_proc_async(proc: asyncio.subprocess.Process) -> None:
    try:
        if proc.returncode is None:
            proc.terminate()
            await asyncio.wait_for(proc.wait(), timeout=0.5)
    except Exception:
        pass

    try:
        if proc.returncode is None:
            proc.kill()
            await asyncio.wait_for(proc.wait(), timeout=0.5)
    except Exception:
        return
