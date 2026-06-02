#!/bin/bash
# Run the WAF reviewer on the bad_agent example

set -e

echo ""
echo "══════════════════════════════════════════════════════"
echo "  Agent WAF Reviewer — demo"
echo "══════════════════════════════════════════════════════"
echo ""

# Check API key
if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "Error: ANTHROPIC_API_KEY is not set."
  echo "Run: export ANTHROPIC_API_KEY=sk-ant-..."
  exit 1
fi

# Check venv
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate

echo "Installing dependencies..."
pip install anthropic --quiet

echo ""
echo "Reviewing: examples/bad_agent"
echo "──────────────────────────────────────────────────────"
python3 agent.py ./examples/bad_agent

echo ""
echo "──────────────────────────────────────────────────────"
echo "To review your own agent:"
echo "  python3 agent.py ./path/to/your/agent"
echo "──────────────────────────────────────────────────────"
