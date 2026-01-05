import asyncio

from codex_sdk import Codex


async def main() -> None:
    codex = Codex()
    thread = codex.start_thread()
    turn = await thread.run_async("Summarize repository status")
    print(turn.final_response)


if __name__ == "__main__":
    asyncio.run(main())
