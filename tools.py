"""
Tool definitions and implementations for agent-waf-reviewer.

Tools give the agent the ability to read and search the target codebase.
"""

import os
import re
import subprocess


# ─────────────────────────────────────────────
# DEFINITIONS
# ─────────────────────────────────────────────

DEFINITIONS = [
    {
        "name": "list_files",
        "description": (
            "List all Python files in a directory recursively. "
            "Use this first to discover what files exist in the agent codebase being reviewed."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The directory path to scan for Python files.",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "read_file",
        "description": (
            "Read the full contents of a file. "
            "Use this to examine agent.py, tools.py, server.py, or any other source file "
            "in the codebase being reviewed."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The absolute or relative file path to read.",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "search_code",
        "description": (
            "Search for a pattern across all Python files in a directory. "
            "Use this to check whether a specific pattern (e.g. 'max_iterations', 'shell=True', "
            "'stop_reason') exists anywhere in the codebase."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The directory to search in.",
                },
                "pattern": {
                    "type": "string",
                    "description": "The regex pattern to search for.",
                },
            },
            "required": ["path", "pattern"],
        },
    },
    {
        "name": "run_pillar_checks",
        "description": (
            "Run automated static analysis checks for all 6 pillars of the "
            "Well-Architected Framework for AI Agents against the codebase at the given path. "
            "Use this after reading the main agent files to get an automated baseline review. "
            "Returns a structured list of findings per pillar."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The root directory of the agent codebase to review.",
                }
            },
            "required": ["path"],
        },
    },
]


# ─────────────────────────────────────────────
# IMPLEMENTATIONS
# ─────────────────────────────────────────────

def list_files(path: str) -> str:
    """List all Python, YAML, JSON, and shell files in a directory."""
    if ".." in path:
        return "Error: invalid path"

    extensions = (".py", ".yaml", ".yml", ".json", ".sh", ".md", ".toml")
    found = []
    try:
        for root, dirs, files in os.walk(path):
            # Skip hidden dirs and venv
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("venv", ".venv", "__pycache__", "node_modules")]
            for f in files:
                if f.endswith(extensions):
                    rel = os.path.relpath(os.path.join(root, f), path)
                    found.append(rel)
    except Exception as e:
        return f"Error: {e}"

    if not found:
        return f"No relevant files found in {path}"
    return "\n".join(sorted(found))


def read_file(path: str, max_chars: int = 4000) -> str:
    """Read a file, truncating if it exceeds max_chars."""
    if ".." in path:
        return "Error: invalid path"
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        if len(content) > max_chars:
            return content[:max_chars] + f"\n\n... [truncated — {len(content)} total chars]"
        return content
    except FileNotFoundError:
        return f"Error: file not found: {path}"
    except Exception as e:
        return f"Error reading {path}: {e}"


def search_code(path: str, pattern: str) -> str:
    """Search for a regex pattern across all Python files in a directory."""
    if ".." in path:
        return "Error: invalid path"
    try:
        result = subprocess.run(
            ["grep", "-rn", "--include=*.py", pattern, path],
            capture_output=True, text=True, timeout=15
        )
        output = result.stdout.strip()
        if not output:
            return f"Pattern '{pattern}' not found in {path}"
        lines = output.split("\n")
        if len(lines) > 30:
            lines = lines[:30] + [f"... [{len(lines) - 30} more matches]"]
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


def run_pillar_checks(path: str) -> str:
    """Run all rubric checks against the codebase and return structured findings."""
    from rubric import CHECKS, PILLARS

    # Collect all Python source code
    all_code = ""
    file_count = 0
    try:
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("venv", ".venv", "__pycache__")]
            for f in files:
                if f.endswith(".py"):
                    fpath = os.path.join(root, f)
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="replace") as fh:
                            all_code += f"\n# === {f} ===\n" + fh.read()
                        file_count += 1
                    except Exception:
                        pass
    except Exception as e:
        return f"Error reading codebase: {e}"

    if not all_code:
        return "No Python files found."

    # Run each check
    findings = {p: [] for p in PILLARS}

    for check in CHECKS:
        passed = False
        flagged = False

        # Check for good patterns
        if check["patterns"]:
            for pat in check["patterns"]:
                if re.search(pat, all_code, re.IGNORECASE):
                    passed = True
                    break

        # Check for anti-patterns
        for pat in check["anti_patterns"]:
            if re.search(pat, all_code, re.IGNORECASE):
                flagged = True
                break

        if flagged:
            status = "❌ FAIL"
        elif check["patterns"] and not passed:
            status = {"FAIL": "❌ FAIL", "WARN": "⚠️  WARN", "INFO": "ℹ️  INFO"}[check["severity"]]
        else:
            status = "✅ PASS"

        findings[check["pillar"]].append({
            "id": check["id"],
            "name": check["name"],
            "status": status,
            "description": check["description"],
        })

    # Compact output — pass lines are short, only failures get descriptions
    lines = [f"WAF checks ({file_count} files scanned)"]
    total_pass = total_checks = 0

    for pillar_num, pillar_name in PILLARS.items():
        checks = findings[pillar_num]
        passes = sum(1 for c in checks if c["status"] == "✅ PASS")
        total = len(checks)
        total_pass += passes
        total_checks += total
        overall = "PASS" if passes == total else ("FAIL" if any("FAIL" in c["status"] for c in checks) else "WARN")
        lines.append(f"\nP{pillar_num} {pillar_name} [{overall}] {passes}/{total}")
        for c in checks:
            lines.append(f"  {c['status']} [{c['id']}] {c['name']}")
            if ("FAIL" in c["status"] or "WARN" in c["status"]) and c["description"]:
                # Truncate description to keep output tight
                desc = c["description"][:120] + ("…" if len(c["description"]) > 120 else "")
                lines.append(f"    → {desc}")

    lines.append(f"\nTOTAL: {total_pass}/{total_checks} checks passing")
    return "\n".join(lines)


# ─────────────────────────────────────────────
# DISPATCHER
# ─────────────────────────────────────────────

def dispatch(tool_name: str, tool_input: dict) -> str:
    match tool_name:
        case "list_files":
            return list_files(tool_input.get("path", "."))
        case "read_file":
            return read_file(tool_input.get("path", ""))
        case "search_code":
            return search_code(tool_input.get("path", "."), tool_input.get("pattern", ""))
        case "run_pillar_checks":
            return run_pillar_checks(tool_input.get("path", "."))
        case _:
            return f"Error: unknown tool '{tool_name}'"
