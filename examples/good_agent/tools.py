"""
GOOD AGENT tools — follows security and reliability best practices.
"""

import subprocess
import logging
import re

logger = logging.getLogger(__name__)

DEFINITIONS = [
    {
        "name": "check_server_status",
        "description": (
            "Returns the current server status including uptime, CPU, and memory usage. "
            "This is a read-only operation. Use this to check if the server is healthy."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "list_log_files",
        "description": (
            "Lists log files in /var/log older than N days. "
            "Use this before deciding which files to clean up."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "older_than_days": {
                    "type": "integer",
                    "description": "Only list files older than this many days (default: 7).",
                }
            },
        },
    },
    {
        "name": "delete_log_file",
        "description": (
            "Deletes a specific log file by exact path. "
            "This action is irreversible — a human must approve before this runs."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The exact path of the log file to delete.",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "read_file",
        "description": (
            "Reads up to 8000 characters of a text file. "
            "Use this to inspect log file contents or configuration files."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The file path to read.",
                }
            },
            "required": ["path"],
        },
    },
]


def check_server_status() -> str:
    try:
        uptime = subprocess.run(["uptime"], capture_output=True, text=True, timeout=5)
        return uptime.stdout.strip() or "uptime returned no output"
    except Exception as e:
        return f"Error checking server status: {e}"


def list_log_files(older_than_days: int = 7) -> str:
    # Validate input
    if not isinstance(older_than_days, int) or older_than_days < 0:
        return "Error: older_than_days must be a non-negative integer"
    try:
        result = subprocess.run(
            ["find", "/var/log", "-name", "*.log", "-mtime", f"+{older_than_days}"],
            capture_output=True, text=True, timeout=10
        )
        output = result.stdout.strip()
        lines = output.split("\n") if output else []
        if len(lines) > 50:
            lines = lines[:50] + [f"... [{len(lines)-50} more files]"]
        return "\n".join(lines) if lines else f"No log files older than {older_than_days} days found."
    except Exception as e:
        return f"Error listing log files: {e}"


def delete_log_file(path: str) -> str:
    # Input validation — only allow paths inside /var/log
    if not path.startswith("/var/log/"):
        return "Error: can only delete files inside /var/log/"
    if ".." in path:
        return "Error: invalid path"
    if not re.match(r"^[a-zA-Z0-9/_.\-]+$", path):
        return "Error: path contains invalid characters"

    # HITL gate — risky action requires human approval
    print(f"\n⚠️  Agent wants to delete: {path}")
    approval = input("Approve deletion? [y/N]: ").strip().lower()
    if approval != "y":
        return f"Deletion of {path} cancelled by human operator."

    try:
        result = subprocess.run(
            ["rm", path],  # list form — no shell=True
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return f"Error deleting {path}: {result.stderr.strip()}"
        return f"Deleted: {path}"
    except Exception as e:
        return f"Error: {e}"


def read_file(path: str, max_chars: int = 8000) -> str:
    if ".." in path:
        return "Error: invalid path"
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        if len(content) > max_chars:
            return content[:max_chars] + f"\n... [truncated — {len(content)} total chars]"
        return content
    except FileNotFoundError:
        return f"Error: file not found: {path}"
    except Exception as e:
        return f"Error: {e}"


def dispatch(tool_name: str, tool_input: dict, run_id: str = "", iteration: int = 0) -> str:
    logger.debug(f"[{run_id}] dispatch: {tool_name} iter={iteration}")
    match tool_name:
        case "check_server_status":
            return check_server_status()
        case "list_log_files":
            return list_log_files(tool_input.get("older_than_days", 7))
        case "delete_log_file":
            return delete_log_file(tool_input.get("path", ""))
        case "read_file":
            return read_file(tool_input.get("path", ""))
        case _:
            return f"Error: unknown tool '{tool_name}'"
