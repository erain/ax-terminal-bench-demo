#!/usr/bin/env python3
"""Grade the fix-git demo.

Replicates tests/test_outputs.py from harbor-framework/terminal-bench-2:
the recovered files must md5-match the reference patch files.
Writes /workspace/results.json (the AX runner does not report the command's
exit status, so the JSON file is the durable record).
"""
import hashlib
import json
import os
import sys
import datetime

TASK_DIR = "/workspace/task"
RESULTS = "/workspace/results.json"


def md5(path):
    with open(path, "rb") as f:
        return hashlib.md5(f.read().strip()).hexdigest()


def main():
    agent = os.environ.get("AGENT", "script")
    tests = [
        ("test_about_file",
         f"{TASK_DIR}/personal-site/_includes/about.md",
         f"{TASK_DIR}/resources/patch_files/about.md"),
        ("test_layout_file",
         f"{TASK_DIR}/personal-site/_layouts/default.html",
         f"{TASK_DIR}/resources/patch_files/default.html"),
    ]
    results = []
    passed = True
    for name, new_path, ref_path in tests:
        try:
            ok = md5(new_path) == md5(ref_path)
            detail = "md5 match" if ok else "md5 MISMATCH"
        except FileNotFoundError as e:
            ok, detail = False, f"missing file: {e.filename}"
        results.append({"name": name, "passed": ok, "detail": detail})
        passed = passed and ok

    report = {
        "task": "terminal-bench-2/fix-git",
        "agent": agent,
        "passed": passed,
        "tests": results,
        "graded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    with open(RESULTS, "w") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
