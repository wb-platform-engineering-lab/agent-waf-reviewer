"""
Review rubric for the Well-Architected Framework for AI Agents.

Each pillar has a list of checks. Each check defines:
  - id:          unique identifier
  - pillar:      pillar number (1-6)
  - name:        short name
  - description: what the reviewer looks for
  - severity:    FAIL | WARN | INFO
  - patterns:    code patterns that indicate the check passes (regex)
  - anti_patterns: code patterns that indicate a problem (regex)
"""

PILLARS = {
    1: "Governance & Control",
    2: "Security",
    3: "Reliability",
    4: "Cost Optimization",
    5: "Observability",
    6: "Performance & Context",
}

CHECKS = [

    # ── Pillar 1 — Governance & Control ──────────────────────────────

    {
        "id": "P1-001",
        "pillar": 1,
        "name": "Max iterations guard",
        "description": "Agent loop must have a maximum iterations limit to prevent infinite loops.",
        "severity": "FAIL",
        "patterns": [r"max_iterations", r"max_turns", r"iteration.*>=", r"range\(max_"],
        "anti_patterns": [],
    },
    {
        "id": "P1-002",
        "pillar": 1,
        "name": "HITL gate for risky tools",
        "description": "Tools with side effects (deploy, delete, send) must have human approval before execution.",
        "severity": "FAIL",
        "patterns": [r"input\(", r"approval", r"confirm", r"human.*approv", r"approv.*human", r"hitl"],
        "anti_patterns": [],
    },
    {
        "id": "P1-003",
        "pillar": 1,
        "name": "Tool definitions list is explicit",
        "description": "The DEFINITIONS or TOOLS list must be defined explicitly — the agent's tool surface must be visible.",
        "severity": "FAIL",
        "patterns": [r"DEFINITIONS\s*=\s*\[", r"TOOLS\s*=\s*\[", r"tools\s*=\s*\["],
        "anti_patterns": [],
    },
    {
        "id": "P1-004",
        "pillar": 1,
        "name": "State machine transitions validated",
        "description": "If the agent manages state transitions, valid transitions should be enforced at the tool level.",
        "severity": "WARN",
        "patterns": [r"VALID_TRANSITIONS", r"valid_transitions", r"allowed_transitions"],
        "anti_patterns": [],
    },
    {
        "id": "P1-005",
        "pillar": 1,
        "name": "HITL not only in system prompt",
        "description": "HITL enforcement should be in code, not only in the system prompt string.",
        "severity": "WARN",
        "patterns": [],
        "anti_patterns": [r"(always ask|ask before|confirm before|never delete|never deploy).*system_prompt"],
    },

    # ── Pillar 2 — Security ───────────────────────────────────────────

    {
        "id": "P2-001",
        "pillar": 2,
        "name": "No shell=True with dynamic input",
        "description": "subprocess.run() must not use shell=True with model-provided arguments — command injection risk.",
        "severity": "FAIL",
        "patterns": [],
        "anti_patterns": [r"subprocess\.run\(.*shell\s*=\s*True"],
    },
    {
        "id": "P2-002",
        "pillar": 2,
        "name": "Input validation before execution",
        "description": "Tool inputs should be validated before being passed to shell, database, or filesystem.",
        "severity": "FAIL",
        "patterns": [r"if.*\.\." , r"validate", r"sanitize", r"re\.match", r"re\.sub", r"\.strip\(\)", r"raise.*Error"],
        "anti_patterns": [],
    },
    {
        "id": "P2-003",
        "pillar": 2,
        "name": "Prompt injection defense in system prompt",
        "description": "System prompt should explicitly address that tool results are untrusted data.",
        "severity": "WARN",
        "patterns": [r"untrusted", r"do not follow.*instructions.*content", r"treat.*as data", r"injection"],
        "anti_patterns": [],
    },
    {
        "id": "P2-004",
        "pillar": 2,
        "name": "No secrets or PII passed to model",
        "description": "Tool results should be checked for secrets/PII before being sent to the model API.",
        "severity": "WARN",
        "patterns": [r"redact", r"mask", r"REDACTED", r"re\.sub.*key", r"re\.sub.*password"],
        "anti_patterns": [r"os\.environ.*content", r"api_key.*content", r"password.*messages"],
    },
    {
        "id": "P2-005",
        "pillar": 2,
        "name": "MCP server uses list-form subprocess",
        "description": "MCP server tools that call subprocesses should use list-form args, not shell strings.",
        "severity": "FAIL",
        "patterns": [r"subprocess\.run\(\["],
        "anti_patterns": [r"subprocess\.run\(f['\"]", r"subprocess\.run\(['\"].*\+"],
    },

    # ── Pillar 3 — Reliability ────────────────────────────────────────

    {
        "id": "P3-001",
        "pillar": 3,
        "name": "Tool errors returned as strings",
        "description": "Tools should return error messages as strings, not raise exceptions that crash the loop.",
        "severity": "FAIL",
        "patterns": [r"return.*[Ee]rror", r"return f\"[Ee]rror", r"except.*return"],
        "anti_patterns": [],
    },
    {
        "id": "P3-002",
        "pillar": 3,
        "name": "Subprocess timeout set",
        "description": "subprocess.run() calls should have a timeout to prevent hanging.",
        "severity": "WARN",
        "patterns": [r"timeout\s*="],
        "anti_patterns": [],
    },
    {
        "id": "P3-003",
        "pillar": 3,
        "name": "stop_reason checked correctly",
        "description": "Agent loop must check stop_reason == 'end_turn' to know when to stop.",
        "severity": "FAIL",
        "patterns": [r"stop_reason.*end_turn", r"end_turn.*stop_reason"],
        "anti_patterns": [],
    },
    {
        "id": "P3-004",
        "pillar": 3,
        "name": "Exception handling in agent loop",
        "description": "Agent loop should handle exceptions from tool calls gracefully.",
        "severity": "WARN",
        "patterns": [r"try:", r"except Exception", r"except.*Error"],
        "anti_patterns": [],
    },

    # ── Pillar 4 — Cost Optimization ─────────────────────────────────

    {
        "id": "P4-001",
        "pillar": 4,
        "name": "Token budget enforcement",
        "description": "Agent should track total tokens used and stop when a budget ceiling is exceeded.",
        "severity": "WARN",
        "patterns": [r"max_tokens", r"token.*budget", r"usage\.input_tokens", r"total_tokens"],
        "anti_patterns": [],
    },
    {
        "id": "P4-002",
        "pillar": 4,
        "name": "Large tool results truncated",
        "description": "Tool results should be truncated or summarized before appending to messages history.",
        "severity": "WARN",
        "patterns": [r"max_chars", r"truncat", r"\[:.*\]", r"\.strip\(\)", r"max_length"],
        "anti_patterns": [],
    },
    {
        "id": "P4-003",
        "pillar": 4,
        "name": "Model specified explicitly",
        "description": "The model name should be explicitly specified, not left to default.",
        "severity": "INFO",
        "patterns": [r"model\s*=\s*[\"']claude"],
        "anti_patterns": [],
    },

    # ── Pillar 5 — Observability ──────────────────────────────────────

    {
        "id": "P5-001",
        "pillar": 5,
        "name": "Tool calls logged",
        "description": "Every tool call should be logged with at minimum tool name, input, and result.",
        "severity": "FAIL",
        "patterns": [r"log", r"print.*tool", r"logger\.", r"logging\.", r"audit"],
        "anti_patterns": [],
    },
    {
        "id": "P5-002",
        "pillar": 5,
        "name": "Run ID or trace ID present",
        "description": "Each agent run should have a unique identifier for tracing and incident investigation.",
        "severity": "WARN",
        "patterns": [r"run_id", r"trace_id", r"uuid", r"UUID"],
        "anti_patterns": [],
    },
    {
        "id": "P5-003",
        "pillar": 5,
        "name": "Token usage tracked",
        "description": "Token usage should be tracked and logged per run for cost observability.",
        "severity": "WARN",
        "patterns": [r"usage\.input_tokens", r"usage\.output_tokens", r"token.*count"],
        "anti_patterns": [],
    },

    # ── Pillar 6 — Performance & Context ─────────────────────────────

    {
        "id": "P6-001",
        "pillar": 6,
        "name": "RAG or chunking for large corpora",
        "description": "If the agent processes large document sets, RAG or map-reduce should be used.",
        "severity": "INFO",
        "patterns": [r"chromadb", r"chroma", r"vector", r"embed", r"chunk", r"map_reduce", r"retrieve"],
        "anti_patterns": [],
    },
    {
        "id": "P6-002",
        "pillar": 6,
        "name": "Episodic or external memory used",
        "description": "For multi-session agents, memory should be persisted externally, not only in context.",
        "severity": "INFO",
        "patterns": [r"sqlite", r"sqlite3", r"memory\.db", r"json\.dump", r"json\.load", r"pickle"],
        "anti_patterns": [],
    },
    {
        "id": "P6-003",
        "pillar": 6,
        "name": "Context not unbounded",
        "description": "Messages history should not grow unbounded — old messages should be pruned or summarized.",
        "severity": "WARN",
        "patterns": [r"messages\[-", r"messages\[:", r"prune", r"summarize.*messages", r"trim.*messages"],
        "anti_patterns": [],
    },
]
