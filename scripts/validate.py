#!/usr/bin/env python3
"""Validate ax/task.yaml against the AX ax.io/v1alpha1 schema.

Checks apiVersion/kind, required metadata, and per-kind spec fields based on
google/ax pkg/apis/v1alpha1/ax.proto. No cluster needed.
"""
import sys

try:
    import yaml
except ImportError:
    print("PyYAML required: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

errors = []


def err(msg):
    errors.append(msg)


def check(cond, msg):
    if not cond:
        err(msg)


def validate_doc(doc, idx):
    tag = f"doc[{idx}]"
    check(isinstance(doc, dict), f"{tag}: not a mapping")
    if not isinstance(doc, dict):
        return
    check(doc.get("apiVersion") == "ax.io/v1alpha1",
          f"{tag}: apiVersion must be ax.io/v1alpha1")
    kind = doc.get("kind")
    check(kind in ("Task", "Workspace", "Model"), f"{tag}: unknown kind {kind!r}")
    meta = doc.get("metadata") or {}
    check(isinstance(meta.get("name"), str) and meta["name"],
          f"{tag}: metadata.name required")
    spec = doc.get("spec")
    check(isinstance(spec, dict), f"{tag}: spec must be a mapping")
    if not isinstance(spec, dict):
        return
    if kind == "Task":
        check(isinstance(spec.get("command"), list) and spec["command"],
              f"{tag}: spec.command must be a non-empty list")
        for e in spec.get("env", []) or []:
            check("name" in e and "value" in e, f"{tag}: env entries need name+value")
        for w in spec.get("workspaces", []) or []:
            check("name" in w and "path" in w,
                  f"{tag}: workspaces entries need name+path")
    elif kind == "Workspace":
        for g in spec.get("git", []) or []:
            check("repo" in g, f"{tag}: git entries need repo")
    elif kind == "Model":
        check("provider" in spec and "model" in spec,
              f"{tag}: Model spec needs provider+model")


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "ax/task.yaml"
    with open(path) as f:
        docs = [d for d in yaml.safe_load_all(f) if d]
    check(docs, "no documents found")
    for i, d in enumerate(docs):
        validate_doc(d, i)
    # Cross-doc check: every Task workspace ref must match a Workspace name.
    names = {d.get("metadata", {}).get("name")
             for d in docs if d.get("kind") == "Workspace"}
    for i, d in enumerate(docs):
        if d.get("kind") == "Task":
            for w in (d.get("spec", {}).get("workspaces") or []):
                check(w.get("name") in names,
                      f"doc[{i}]: Task references unknown Workspace {w.get('name')!r}")
    if errors:
        print("VALIDATION FAILED:")
        for e in errors:
            print(" -", e)
        return 1
    print(f"OK: {path} ({len(docs)} documents) conforms to ax.io/v1alpha1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
