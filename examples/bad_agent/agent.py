"""
BAD AGENT — intentionally violates multiple WAF pillars.
Used as a review target to demonstrate the reviewer's findings.

Violations:
  P1: no max_iterations, no HITL gate, HITL only in system prompt
  P2: shell=True with user input, no input validation
  P3: exceptions crash the loop, no stop_reason check
  P4: no token budget, no result truncation
  P5: no logging, no run ID
  P6: no memory, context grows unbounded
"""

import anthropic
import tools

client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are a helpful DevOps assistant.
Always ask for confirmation before running destructive commands.
Never delete files without asking first.
"""

def run_agent(goal: str):
    messages = [{"role": "user", "content": goal}]

    while True:  # no max_iterations guard
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=tools.DEFINITIONS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    print(block.text)
            return

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = tools.dispatch(block.name, block.input)  # no logging
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})


if __name__ == "__main__":
    run_agent("Check the server status and clean up old log files.")
