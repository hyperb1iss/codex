# Codex Python SDK (WIP)

This is a Python SDK for interacting with the Codex agent by wrapping the local `codex` CLI.

It mirrors the TypeScript SDK (`sdk/typescript`) at a high level:

- Spawns `codex exec --experimental-json`
- Writes the prompt to stdin
- Reads JSONL events from stdout

## Requirements

- Python 3.9+
- `codex` installed and available on `PATH` (or pass `CodexOptions(codex_path_override=...)`)

## Development

From `sdk/python`:

```bash
uv sync
uv run ruff format .
uv run ruff check .
uv run pyright
uv run python -m unittest discover -s tests -p "test_*.py"
```

## Quickstart

```python
from codex_sdk import Codex

codex = Codex()
thread = codex.start_thread()
turn = thread.run("Summarize repository status")

print(turn.final_response)
print(turn.items)
```

## Streaming responses

```python
from codex_sdk import Codex

codex = Codex()
thread = codex.start_thread()
streamed = thread.run_streamed("Diagnose the test failure and propose a fix")

for event in streamed.events:
    if event["type"] == "item.completed":
        print(event["item"])
```

## Structured output

```python
from codex_sdk import Codex, TurnOptions

schema = {
  "type": "object",
  "properties": {"summary": {"type": "string"}},
  "required": ["summary"],
  "additionalProperties": False,
}

codex = Codex()
thread = codex.start_thread()
turn = thread.run("Summarize repository status", TurnOptions(output_schema=schema))
print(turn.final_response)
```

## Images

```python
from codex_sdk import Codex

codex = Codex()
thread = codex.start_thread()
turn = thread.run([
    {"type": "text", "text": "Describe these screenshots"},
    {"type": "local_image", "path": "./ui.png"},
])
print(turn.final_response)
```

## Resuming an existing thread

```python
import os
from codex_sdk import Codex

codex = Codex()
thread = codex.resume_thread(os.environ["CODEX_THREAD_ID"])
turn = thread.run("Continue from where we left off")
```

## Working directory controls

Codex runs in the current working directory by default. To avoid unrecoverable errors, Codex requires the working directory to be a Git repository. You can skip the Git repository check by passing `skip_git_repo_check` when creating a thread.

```python
from codex_sdk import Codex, ThreadOptions

codex = Codex()
thread = codex.start_thread(
    ThreadOptions(working_directory="/path/to/project", skip_git_repo_check=True)
)
turn = thread.run("Summarize repository status")
print(turn.final_response)
```

## Controlling the Codex CLI environment

By default, the Codex CLI inherits the Python process environment. Provide the optional `env` parameter when instantiating the `Codex` client to fully control which variables the CLI receives—useful for sandboxed hosts.

```python
from codex_sdk import Codex, CodexOptions

codex = Codex(CodexOptions(env={"PATH": "/usr/local/bin"}))
thread = codex.start_thread()
turn = thread.run("Summarize repository status")
print(turn.final_response)
```

The SDK still injects required variables (such as `OPENAI_BASE_URL` and `CODEX_API_KEY`) on top of the environment you provide.

## Cancellation and timeouts

```python
from codex_sdk import CancelToken, Codex, TurnOptions

token = CancelToken()
codex = Codex()
thread = codex.start_thread()

# token.cancel() from another thread to abort.
turn = thread.run("Long-running request", TurnOptions(timeout_s=30, cancel_token=token))
```

## Asyncio

```python
import asyncio
from codex_sdk import Codex

async def main() -> None:
    codex = Codex()
    thread = codex.start_thread()
    turn = await thread.run_async("Summarize repository status")
    print(turn.final_response)

asyncio.run(main())
```
