import os

from codex_sdk import Codex


def main() -> None:
    thread_id = os.environ["CODEX_THREAD_ID"]
    codex = Codex()
    thread = codex.resume_thread(thread_id)
    turn = thread.run("Continue from where we left off")
    print(turn.final_response)


if __name__ == "__main__":
    main()
