# Terminal-Bench 2.0 `fix-git` on AX

An end-to-end example of running an agentic workload on
[AX](https://agentexecutor.io) (Google's open agentic orchestration runtime,
`github.com/google/ax`).

The demo runs Terminal-Bench 2.0's `fix-git` task
([harbor-framework/terminal-bench-2](https://github.com/harbor-framework/terminal-bench-2/tree/main/fix-git)):
an agent must recover commits lost on a detached HEAD and merge them back
into `master`. Grading reuses the upstream md5-hash tests.

## Why this shape

Harbor (the TB 2.0 runner) executes each task inside its own Docker
container. AX sandboxes are gVisor/microVM actors where Docker-in-Docker is
not practical, so this demo is **AX-native**: the TB task scenario is
recreated directly in the task sandbox filesystem (`demo/setup-task.sh`
mirrors the upstream `environment/setup.sh` but needs no network), the
agent runs as the Task's `spec.command`, and grading writes
`/workspace/results.json` (the AX runner does not report the command's exit
status back, so the JSON file is the durable record).

## Repo layout

```
ax/task.yaml          # Workspace + Task manifests (apply with `ax apply -f`)
demo/run-demo.sh      # Task entrypoint: setup -> agent -> grade -> results.json
demo/setup-task.sh    # hermetic fix-git scenario setup (no network needed)
demo/agent.py         # minimal LLM agent (OpenAI-compatible API + bash tool, stdlib only)
demo/solve-reference.sh # deterministic reference solver (fallback agent)
demo/grade.py         # upstream md5 grading -> /workspace/results.json
demo/instruction.md   # task prompt given to the LLM agent
scripts/validate.py   # offline manifest schema validation (no cluster needed)
```

## Run it

Prerequisites: a Kubernetes cluster with Agent Substrate and the AX control
plane deployed, plus the `ax` CLI
([quick start](https://github.com/google/ax#quick-start)).

```bash
# 1. Validate manifests offline (no cluster needed)
python3 scripts/validate.py

# 2. Put your key in (see Security note below), then apply
ax apply -f ax/task.yaml

# 3. Watch and inspect
ax watch task tb-fix-git-demo
ax ssh tb-fix-git-demo -- cat /workspace/results.json
ax ssh tb-fix-git-demo -- git -C /workspace/task/personal-site log --oneline --graph -5
```

`results.json` looks like:

```json
{
  "task": "terminal-bench-2/fix-git",
  "agent": "llm",
  "passed": true,
  "tests": [
    {"name": "test_about_file", "passed": true, "detail": "md5 match"},
    {"name": "test_layout_file", "passed": true, "detail": "md5 match"}
  ],
  "graded_at": "2026-10-12T..."
}
```

## Agent selection

`AGENT` env (default `auto`):

- `llm` — real agentic run: `demo/agent.py`, a minimal tool-using agent
  (stdlib only, no installs) that talks to any OpenAI-compatible
  chat-completions API with a single `bash` tool. Configure via
  `LLM_BASE_URL` / `LLM_MODEL` / `LLM_API_KEY`. Defaults: DeepSeek
  (`https://api.deepseek.com/v1`, `deepseek-chat`); Zhipu GLM
  (`https://open.bigmodel.cn/api/paas/v4`, `glm-4.5-air`) works the same.
  Whichever provider you use, the key needs available quota — a key with no
  balance returns an error and the demo falls back to grading whatever is
  in the repo (see `results.json`).
- `script` — deterministic reference solver (`demo/solve-reference.sh`).
  Always works; useful for smoke-testing the plumbing.
- `auto` — uses the LLM agent when a real key is present, else the
  reference solver.

## Security note

`ax.io/v1alpha1` Task `env` entries are plain `name`/`value` pairs — there is
no `secretKeyRef` for Task env today (unlike `Model.spec.secretKey`). **Do
not commit your real API key.** Keep `ax/task.yaml` local-only after editing,
or inject the key at apply time without touching the file, e.g.:

```bash
LLM_API_KEY=... ax apply -f <(envsubst < ax/task.yaml)
```

(The committed manifest ships with `PASTE_YOUR_KEY_HERE`.)

## Verified

- `scripts/validate.py`: manifests conform to `ax.io/v1alpha1`.
- Workload logic executed end-to-end locally (setup -> solver -> grading ->
  `results.json` passes).
- Not yet run: `ax apply` against a live AX cluster (needs your cluster).
- The LLM agent path (`demo/agent.py`) is provider-agnostic; point
  `LLM_BASE_URL`/`LLM_MODEL` at any OpenAI-compatible endpoint.

## Upstream sources

- Task definition: `harbor-framework/terminal-bench-2/fix-git`
  (task.toml, environment/, tests/, solution/)
- AX API: `google/ax` `pkg/apis/v1alpha1/ax.proto`
