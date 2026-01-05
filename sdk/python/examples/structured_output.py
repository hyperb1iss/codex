from codex_sdk import Codex, TurnOptions


def main() -> None:
    schema = {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "status": {"type": "string", "enum": ["ok", "action_required"]},
        },
        "required": ["summary", "status"],
        "additionalProperties": False,
    }

    codex = Codex()
    thread = codex.start_thread()
    turn = thread.run("Summarize repository status", TurnOptions(output_schema=schema))
    print(turn.final_response)


if __name__ == "__main__":
    main()
