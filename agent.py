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
import report as r

# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────

MODEL = "claude-haiku-4-5-20251001"
MAX_ITERATIONS = 15
MAX_TOKENS_INPUT = 80_000
MAX_OUTPUT_TOKENS = 6144

SYSTEM_PROMPT = """You are an expert AI agent architect conducting a Well-Architected Framework review.

You review AI agent codebases against 6 pillars:
1. Governance & Control — Tool ACL, HITL gates, state machines, break-glass
2. Security — Least privilege, prompt injection defense, input validation, no shell=True
3. Reliability — Loop termination, error recovery, stop_reason handling
4. Cost Optimization — Token budgets, context pruning, model routing
5. Observability — Audit logging, run IDs, token tracking
6. Performance & Context — RAG, episodic memory, context management

Your review process — follow this order strictly:
1. Call list_files to discover the codebase structure
2. Call read_file on agent.py and tools.py only (maximum 2 read_file calls total)
3. Call run_pillar_checks IMMEDIATELY after reading — this runs all 23 checks at once
4. STOP calling tools. Write the final report immediately after run_pillar_checks.

CRITICAL: After run_pillar_checks returns, do NOT call any more tools (no more read_file, no search_code).
Write the report immediately using the automated check results.

Your final report must include:
- A one-line verdict per pillar (PASS / WARN / FAIL) with specific findings
- Concrete recommendations for each failing check referencing actual file/function names
- An overall score (X/6 pillars passing)
- A prioritized action list (top 3 things to fix first)

Only report what you observed. Do not hallucinate findings.
"""


# ─────────────────────────────────────────────
# Agent loop
# ─────────────────────────────────────────────

_TRIM_KEEP = 300   # chars to keep when trimming a read_file result


def _prune_context(messages: list, read_file_ids: set) -> None:
    """Trim read_file tool results in old turns — only read_file, never run_pillar_checks."""
    last_user = max(i for i, m in enumerate(messages) if m["role"] == "user")
    for i, msg in enumerate(messages):
        if i == last_user or msg["role"] != "user":
            continue
        content = msg.get("content", [])
        if not isinstance(content, list):
            continue
        for item in content:
            if (isinstance(item, dict)
                    and item.get("type") == "tool_result"
                    and item.get("tool_use_id") in read_file_ids):
                text = item.get("content", "")
                if isinstance(text, str) and len(text) > _TRIM_KEEP:
                    item["content"] = text[:_TRIM_KEEP] + f"\n... [trimmed — {len(text)} chars total]"


def run_review(target_path: str) -> str:
    client = anthropic.Anthropic()

    goal = f"""Review the AI agent codebase at: {os.path.abspath(target_path)}

Produce a complete Well-Architected Framework review across all 6 pillars.
Start by listing the files, then read the key source files, run the automated checks,
and finish with a structured report and prioritized action list."""

    messages = [{"role": "user", "content": goal}]
    total_tokens = 0
    iteration = 0
    read_file_ids: set = set()   # tracks tool_use_ids for read_file calls
    partial_text: list = []      # accumulates text across max_tokens continuations

    print(f"\n{'═'*60}")
    print(f"  Agent WAF Reviewer")
    print(f"  Target: {os.path.abspath(target_path)}")
    print(f"{'═'*60}\n")

    while iteration < MAX_ITERATIONS:
        iteration += 1
        _prune_context(messages, read_file_ids)

        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_OUTPUT_TOKENS,
            system=SYSTEM_PROMPT,
            tools=t.DEFINITIONS,
            messages=messages,
        )

        total_tokens += response.usage.input_tokens + response.usage.output_tokens
        print(f"[iter {iteration}] stop_reason={response.stop_reason}  tokens={total_tokens:,}")

        if total_tokens > MAX_TOKENS_INPUT:
            return f"[Token budget exceeded at iteration {iteration}] Partial review available."

        # Handle end_turn — combine any accumulated partial text with final block
        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    partial_text.append(block.text)
            return "\n".join(partial_text) if partial_text else "Review complete — no text response generated."

        # Handle max_tokens — collect partial text and ask model to continue
        if response.stop_reason == "max_tokens":
            for block in response.content:
                if hasattr(block, "text"):
                    partial_text.append(block.text)
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": "Please continue your response."})
            continue

        # Handle tool use
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"         tool: {block.name}({list(block.input.keys())})")
                result = t.dispatch(block.name, block.input)
                if block.name == "read_file":
                    read_file_ids.add(block.id)   # mark for future pruning
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

        # Only append if there are actual tool results — empty content causes API error
        if not tool_results:
            continue

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

    review = run_review(target)

    print(f"\n{'═'*60}")
    print("  REVIEW REPORT")
    print(f"{'═'*60}\n")
    print(review)

    # Save HTML report
    output_path = r.save_report(review, target, output_dir=".")
    print(f"\n{'═'*60}")
    print(f"  HTML report saved: {output_path}")
    print(f"{'═'*60}")
