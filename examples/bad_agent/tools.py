"""
BAD AGENT tools — multiple security and reliability violations.
"""

import subprocess

DEFINITIONS = [
    {
        "name": "run_command",
        "description": "Runs a shell command.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The command to run."}
            },
            "required": ["command"],
        },
    },
    {
        "name": "delete_files",
        "description": "Deletes files matching a pattern.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "File pattern to delete."}
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "read_file",
        "description": "Reads a file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"}
            },
            "required": ["path"],
        },
    },
]


def run_command(command: str) -> str:
    # VIOLATION P2-001: shell=True with model-provided input — command injection
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout + result.stderr


def delete_files(pattern: str) -> str:
    # VIOLATION P1-002: no HITL gate — deletes without asking
    # VIOLATION P2-002: no input validation
    result = subprocess.run(
        f"rm -rf {pattern}", shell=True,  # also P2-001
        capture_output=True, text=True
    )
    return f"Deleted: {pattern}"


def read_file(path: str) -> str:
    # VIOLATION P4-002: no truncation — returns full file regardless of size
    with open(path, "r") as f:
        return f.read()


def dispatch(tool_name: str, tool_input: dict) -> str:
    match tool_name:
        case "run_command":
            return run_command(tool_input.get("command", ""))
        case "delete_files":
            return delete_files(tool_input.get("pattern", ""))
        case "read_file":
            return read_file(tool_input.get("path", ""))
        case _:
            return f"Unknown tool: {tool_name}"
