#!/usr/bin/env bash
# Deterministic reference solver for the fix-git demo.
# Used when no LLM agent is configured (AGENT=script). Mirrors the logic of
# the upstream solution/solve.sh: find the lost commit in the reflog,
# branch it, and merge back into master.
set -euo pipefail

cd /workspace/task/personal-site

# Find the lost "Move to Stanford" commit via the reflog.
LOST="$(git log --reflog --format='%H %s' | grep 'Move to Stanford' | head -n1 | awk '{print $1}')"
if [ -z "$LOST" ]; then
  echo "solve-reference: could not find the lost commit in the reflog" >&2
  exit 1
fi
echo "solve-reference: lost commit is $LOST"

git checkout -qb recovery-branch "$LOST"
git checkout -q master
git merge -q -m "Merge recovery-branch into master" -X theirs recovery-branch
echo "solve-reference: merged recovery-branch into master"
