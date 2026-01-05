from codex_sdk import Codex


def main() -> None:
    codex = Codex()
    thread = codex.start_thread()
    turn = thread.run(
        [
            {"type": "text", "text": "Describe these screenshots"},
            {"type": "local_image", "path": "./ui.png"},
        ]
    )
    print(turn.final_response)


if __name__ == "__main__":
    main()
