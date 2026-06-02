"""
agent-waf-reviewer

Reviews an AI agent codebase against the Well-Architected Framework for AI Agents
and produces a structured report across 6 pillars.

Usage:
    python3 agent.py ./path/to/your/agent
    python3 agent.py ./examples/bad_agent
    python3 agent.py ./examples/good_agent
"""

import os
import sys
import anthropic
import tools as t

# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────

MODEL = "claude-sonnet-4-6"
MAX_ITERATIONS = 20
MAX_TOKENS_INPUT = 150_000

SYSTEM_PROMPT = """You are an expert AI agent architect conducting a Well-Architected Framework review.

You review AI agent codebases against 6 pillars:
1. Governance & Control — Tool ACL, HITL gates, state machines, break-glass
2. Security — Least privilege, prompt injection defense, input validation, no shell=True
3. Reliability — Loop termination, error recovery, stop_reason handling
4. Cost Optimization — Token budgets, context pruning, model routing
5. Observability — Audit logging, run IDs, token tracking
6. Performance & Context — RAG, episodic memory, context management

Your review process:
1. Call list_files to discover the codebase structure
2. Call read_file on agent.py, tools.py, and any other key files
3. Call run_pillar_checks to get the automated baseline
4. Search for specific patterns with search_code as needed
5. Produce a final structured report

Your final report must include:
- A one-line verdict per pillar (PASS / WARN / FAIL) with specific findings
- Concrete line-level recommendations for each failing check
- An overall score (X/6 pillars passing)
- A prioritized action list (top 3 things to fix first)

Be specific. Reference actual file names, function names, and line patterns you found.
Do not hallucinate findings — only report what you observed in the code.
"""


# ─────────────────────────────────────────────
# Agent loop
# ─────────────────────────────────────────────

def run_review(target_path: str) -> str:
    client = anthropic.Anthropic()

    goal = f"""Review the AI agent codebase at: {os.path.abspath(target_path)}

Produce a complete Well-Architected Framework review across all 6 pillars.
Start by listing the files, then read the key source files, run the automated checks,
and finish with a structured report and prioritized action list."""

    messages = [{"role": "user", "content": goal}]
    total_tokens = 0
    iteration = 0

    print(f"\n{'═'*60}")
    print(f"  Agent WAF Reviewer")
    print(f"  Target: {os.path.abspath(target_path)}")
    print(f"{'═'*60}\n")

    while iteration < MAX_ITERATIONS:
        iteration += 1

        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=t.DEFINITIONS,
            messages=messages,
        )

        total_tokens += response.usage.input_tokens + response.usage.output_tokens
        print(f"[iter {iteration}] stop_reason={response.stop_reason}  tokens={total_tokens:,}")

        if total_tokens > MAX_TOKENS_INPUT:
            return f"[Token budget exceeded at iteration {iteration}] Partial review available."

        # Handle end_turn — extract final text response
        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return "Review complete — no text response generated."

        # Handle tool use
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"         tool: {block.name}({list(block.input.keys())})")
                result = t.dispatch(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

        # Append assistant response and tool results
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    return f"Review did not complete within {MAX_ITERATIONS} iterations."


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 agent.py <path-to-agent-codebase>")
        print("       python3 agent.py ./examples/bad_agent")
        print("       python3 agent.py ./examples/good_agent")
        sys.exit(1)

    target = sys.argv[1]
    if not os.path.isdir(target):
        print(f"Error: '{target}' is not a directory")
        sys.exit(1)

    report = run_review(target)

    print(f"\n{'═'*60}")
    print("  REVIEW REPORT")
    print(f"{'═'*60}\n")
    print(report)
