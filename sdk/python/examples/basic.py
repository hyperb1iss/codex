from codex_sdk import Codex


def main() -> None:
    codex = Codex()
    thread = codex.start_thread()
    turn = thread.run("Summarize repository status")
    print(turn.final_response)


if __name__ == "__main__":
    main()
