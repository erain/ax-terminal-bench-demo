#!/usr/bin/env bash
# Entry point for the AX Task (spec.command).
# Flow: setup -> agent solves -> grade -> results.json.
#
# AGENT selects the solver:
#   llm    : real agentic run via demo/agent.py (needs LLM_API_KEY)
#   script : deterministic reference solver (default when no key is set)
#   auto   : "llm" when a real key is present, else "script"
set -euo pipefail

AGENT="${AGENT:-auto}"
KEY="${LLM_API_KEY:-}"

if [ "$AGENT" = "auto" ]; then
  if [ -n "$KEY" ] && [ "$KEY" != "PASTE_YOUR_KEY_HERE" ]; then
    AGENT="llm"
  else
    AGENT="script"
  fi
fi
export AGENT

echo "run-demo: agent=$AGENT (model=${LLM_MODEL:-unset})"

# 1. Set up the fix-git scenario.
/workspace/demo/setup-task.sh

# 2. Agent solves it.
if [ "$AGENT" = "llm" ]; then
  echo "run-demo: running LLM agent (demo/agent.py)..."
  set +e
  /workspace/demo/agent.py 2>&1 | tail -n 30
  AGENT_RC=$?
  set -e
  echo "run-demo: agent exited rc=$AGENT_RC"
else
  echo "run-demo: running deterministic reference solver..."
  /workspace/demo/solve-reference.sh
fi

# 3. Grade and record results (durable: the runner keeps /workspace).
echo "run-demo: grading..."
set +e
/workspace/demo/grade.py
GRADE_RC=$?
set -e

echo "run-demo: done. results at /workspace/results.json (grade rc=$GRADE_RC)"
echo "run-demo: the task runner stays up after this script exits; inspect with: ax ssh tb-fix-git-demo -- cat /workspace/results.json"
exit 0
