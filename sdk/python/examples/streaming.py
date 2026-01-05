from codex_sdk import Codex


def main() -> None:
    codex = Codex()
    thread = codex.start_thread()
    streamed = thread.run_streamed("Diagnose the test failure and propose a fix")

    for event in streamed.events:
        if event["type"] == "item.completed":
            print(event["item"])
        elif event["type"] == "turn.completed":
            print("usage", event["usage"])


if __name__ == "__main__":
    main()
