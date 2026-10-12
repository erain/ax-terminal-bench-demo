#!/usr/bin/env bash
# Hermetic setup for the Terminal-Bench 2.0 `fix-git` task.
# Mirrors environment/setup.sh from harbor-framework/terminal-bench-2, but
# builds the scenario locally instead of cloning from GitHub so the demo
# works even with restricted egress.
#
# Scenario: the user committed website changes on a detached HEAD and then
# checked out master, "losing" the changes. The agent must recover them.
set -euo pipefail

TASK_DIR="/workspace/task"
DEMO_DIR="/workspace/demo"

rm -rf "$TASK_DIR"
mkdir -p "$TASK_DIR/resources/patch_files"
cp "$DEMO_DIR/resources/patch_files/about.md" "$TASK_DIR/resources/patch_files/about.md"
cp "$DEMO_DIR/resources/patch_files/default.html" "$TASK_DIR/resources/patch_files/default.html"

git config --global user.email "demo@ax.local" >/dev/null 2>&1 || true
git config --global user.name "AX Demo" >/dev/null 2>&1 || true
git config --global init.defaultBranch master >/dev/null 2>&1 || true

# 1. Create the "personal website" repo on master.
git init -q "$TASK_DIR/personal-site"
cd "$TASK_DIR/personal-site"
mkdir -p _includes _layouts
printf '# My personal site\n' > index.md
printf 'About me (original).\n' > _includes/about.md
printf '<html><body>layout (original)</body></html>\n' > _layouts/default.html
git add -A
git commit -qm "initial site"

# 2. Detached HEAD commit with the "lost" changes (mirrors upstream setup.sh).
git checkout -q --detach HEAD
cp "$TASK_DIR/resources/patch_files/about.md" _includes/about.md
cp "$TASK_DIR/resources/patch_files/default.html" _layouts/default.html
git add -A
git commit -qm "Move to Stanford"

# 3. Back to master: the changes are now only reachable via the reflog.
git checkout -q master

echo "setup-task: scenario ready at $TASK_DIR/personal-site"
echo "setup-task: master is at $(git rev-parse --short HEAD); lost commit is in the reflog"
