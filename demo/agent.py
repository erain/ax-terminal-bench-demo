#!/usr/bin/env python3
"""Minimal tool-using agent for the AX Terminal-Bench 2.0 demo.

Talks to any OpenAI-compatible chat-completions API (GLM, DeepSeek, OpenAI,
...) with a single `bash` tool. Standard library only, so it runs in the
default AX task-runner image with no extra installs.

Env:
  LLM_BASE_URL   e.g. https://api.deepseek.com/v1
  LLM_API_KEY    provider API key
  LLM_MODEL      e.g. deepseek-chat
  AGENT_WORKDIR  default /workspace/task/personal-site
  AGENT_MAX_TURNS default 20
"""
import json
import os
import subprocess
import sys
import urllib.request
import urllib.error

BASE_URL = os.environ["LLM_BASE_URL"].rstrip("/")
API_KEY = os.environ["LLM_API_KEY"]
MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")
WORKDIR = os.environ.get("AGENT_WORKDIR", "/workspace/task/personal-site")
MAX_TURNS = int(os.environ.get("AGENT_MAX_TURNS", "20"))

SYSTEM = """You are solving a git recovery task in the working directory.
The user made changes to their personal site, committed them while on a
detached HEAD, then checked out master. The changes are now "lost".
Find them (hint: `git reflog` shows where HEAD has been) and merge them
into the master branch.

You have one tool: bash. Run any non-interactive shell command in the
working directory and you will see its output.
When the task is complete, reply with a short summary and make no tool calls.
Be efficient: aim for under 15 tool calls."""

TOOLS = [{
    "type": "function",
    "function": {
        "name": "bash",
        "description": "Run a shell command in the task working directory and return its output.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string",
                            "description": "Shell command to run (non-interactive)."}
            },
            "required": ["command"],
        },
    },
}]


def chat(messages):
    body = json.dumps({
        "model": MODEL,
        "messages": messages,
        "tools": TOOLS,
        "tool_choice": "auto",
        "temperature": 0.2,
    }).encode()
    req = urllib.request.Request(
        BASE_URL + "/chat/completions",
        data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + API_KEY},
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"LLM API HTTP {e.code}: {e.read()[:500]!r}")


def run_bash(command):
    try:
        p = subprocess.run(command, shell=True, cwd=WORKDIR,
                           capture_output=True, text=True, timeout=120)
        return f"[exit {p.returncode}]\n{(p.stdout + p.stderr)[-4000:]}"
    except subprocess.TimeoutExpired:
        return "[timeout after 120s]"


def main():
    with open("/workspace/demo/instruction.md") as f:
        instruction = f.read()
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": instruction}]
    for turn in range(1, MAX_TURNS + 1):
        msg = chat(messages)["choices"][0]["message"]
        assistant = {"role": "assistant", "content": msg.get("content")}
        if msg.get("tool_calls"):
            assistant["tool_calls"] = msg["tool_calls"]
        messages.append(assistant)

        calls = msg.get("tool_calls") or []
        if not calls:
            print(f"agent: done after {turn} turn(s)")
            print("agent final:", (msg.get("content") or "")[:500])
            return 0
        for c in calls:
            fn = c["function"]
            if fn["name"] != "bash":
                result = f"unknown tool: {fn['name']}"
            else:
                cmd = json.loads(fn["arguments"])["command"]
                print(f"agent [turn {turn}]: $ {cmd[:160]}", flush=True)
                result = run_bash(cmd)
            messages.append({"role": "tool", "tool_call_id": c["id"],
                             "content": result})
    print("agent: max turns reached without finishing", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
