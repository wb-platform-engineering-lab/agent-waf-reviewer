# agent-waf-reviewer

> An AI agent that reviews AI agent codebases against the **Well-Architected Framework for AI Agents** and produces a scored report across 6 pillars.

No equivalent tool exists for AI agents today. This is the AWS Trusted Advisor for agentic systems.

---

## What it does

Point it at any AI agent codebase. It reads your code, runs automated checks, and produces a structured report:

```
══════════════════════════════════════════════════════════════
  REVIEW REPORT
══════════════════════════════════════════════════════════════

Pillar 1 — Governance & Control      ❌ FAIL   1/5 checks passing
  ❌ FAIL  [P1-001] Max iterations guard
           → Agent loop must have a maximum iterations limit
  ❌ FAIL  [P1-002] HITL gate for risky tools
           → delete_files has no human approval gate
  ✅ PASS  [P1-003] Tool definitions list is explicit

Pillar 2 — Security                  ❌ FAIL   1/5 checks passing
  ❌ FAIL  [P2-001] No shell=True with dynamic input
           → subprocess.run() called with shell=True in tools.py
  ❌ FAIL  [P2-002] Input validation before execution

...

Overall: 8/23 checks passing

TOP 3 ACTIONS:
1. Add max_iterations guard to your agent loop
2. Remove shell=True from subprocess calls — use list form
3. Add a HITL gate to delete_files and any other destructive tools
```

---

## The 6 pillars

| # | Pillar | What it checks |
|---|---|---|
| 1 | Governance & Control | max_iterations guard, HITL gates, Tool ACL, state machines |
| 2 | Security | shell=True, input validation, prompt injection defense, PII redaction |
| 3 | Reliability | stop_reason handling, error recovery, exception handling |
| 4 | Cost Optimization | token budgets, result truncation, model specified |
| 5 | Observability | audit logging, run IDs, token tracking |
| 6 | Performance & Context | RAG, episodic memory, context pruning |

Full framework reference: [Well-Architected Framework for AI Agents](https://github.com/wb-platform-engineering-lab/agent-waf-reviewer/blob/main/docs/well_architected_ai_agents.html)

---

## Getting started

### 1. Clone

```bash
git clone https://github.com/wb-platform-engineering-lab/agent-waf-reviewer.git
cd agent-waf-reviewer
```

### 2. Set up environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install anthropic
```

### 3. Set your API key

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

### 4. Run the demo

```bash
bash run.sh
```

This reviews the `examples/bad_agent` — a deliberately flawed agent that violates all 6 pillars.

### 5. Review your own agent

```bash
python3 agent.py ./path/to/your/agent
```

---

## How it works

```
Your codebase
     ↓
agent.py — sends goal to Claude with 4 tools:
  • list_files       — discovers codebase structure
  • read_file        — reads agent.py, tools.py, etc.
  • search_code      — searches for specific patterns
  • run_pillar_checks — runs 23 automated static checks
     ↓
Claude reads the code, runs checks, reasons about findings
     ↓
Structured report with pillar scores + action list
```

The agent uses:
- **Static analysis** (`run_pillar_checks`) — 23 pattern-based checks across 6 pillars
- **Code reading** — Claude reads actual source files for context-aware findings
- **Targeted search** — `search_code` for specific patterns the automated checks may miss

---

## Examples

### Bad agent — all pillars failing

```
examples/bad_agent/
├── agent.py   ← no max_iterations, no logging, no token tracking
└── tools.py   ← shell=True, no HITL, no input validation, no truncation
```

Review it:
```bash
python3 agent.py ./examples/bad_agent
```

### Good agent — all pillars passing

```
examples/good_agent/
├── agent.py   ← max_iterations, run_id logging, token tracking, exception handling
└── tools.py   ← list-form subprocess, HITL gate, input validation, result truncation
```

Review it:
```bash
python3 agent.py ./examples/good_agent
```

---

## Project structure

```
agent-waf-reviewer/
├── agent.py           ← main agent loop
├── tools.py           ← list_files, read_file, search_code, run_pillar_checks
├── rubric.py          ← 23 checks across 6 pillars (patterns + anti-patterns)
├── run.sh             ← demo script
└── examples/
    ├── bad_agent/     ← intentionally flawed agent (all pillars failing)
    └── good_agent/    ← well-architected agent (all pillars passing)
```

---

## Extending the rubric

Add new checks to `rubric.py`:

```python
{
    "id": "P1-006",
    "pillar": 1,
    "name": "My new check",
    "description": "What this checks for and why it matters.",
    "severity": "FAIL",            # FAIL | WARN | INFO
    "patterns": [r"good_pattern"], # presence = check passes
    "anti_patterns": [r"bad_pat"], # presence = check fails
}
```

---

## Stack

- **LLM**: Claude (`claude-sonnet-4-6`) — Anthropic SDK
- **Static analysis**: Python `re` + `grep`
- **No frameworks**: raw Anthropic SDK — you see exactly what's happening
- **Language**: Python 3.10+

---

## Related

- [AI Agent Fundamentals](https://github.com/wb-platform-engineering-lab/ai-agent-fundamentals) — 13 hands-on projects to understand how AI agents work
- [Well-Architected Framework for AI Agents](https://github.com/wb-platform-engineering-lab/agent-waf-reviewer/blob/main/docs/) — the framework this reviewer is built on
