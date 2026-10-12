#!/usr/bin/env python3
"""Read-only failure diagnostic for SUSFS patch vs audited Xiaomi BSP.

Never applies partial hunks, never generates 'fixed' patch by fuzzy context.
Prints exact failed-file hunks and local source around old hunk line numbers.
"""
import argparse
from pathlib import Path
import re

FAILURE_PATHS = (
    "fs/exec.c",
    "fs/namei.c",
    "fs/proc/base.c",
    "fs/proc/task_mmu.c",
    "mm/memory.c",
)

def diagnose(patch: Path, kernel_tree: Path, *, max_lines_per_file: int = 240):
    content = patch.read_text(encoding="utf-8", errors="replace")
    chunks = re.split(r"(?=^diff --git a/)", content, flags=re.MULTILINE)
    print("========== SUSFS PATCH CONFLICT CONTEXT (read-only) ==========", flush=True)
    for name in FAILURE_PATHS:
        section = next(
            (c for c in chunks if c.startswith(f"diff --git a/{name} b/{name}\n")),
            None,
        )
        if section is None:
            print(f"Patch does not contain {name}. Abort manual port; inspect source.", flush=True)
            continue
        hunks = list(re.finditer(r"(?m)^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", section))
        print(f"\n### {name} — {len(hunks)} patch hunk(s)\n", flush=True)
        used = 0
        source_lines = (kernel_tree / name).read_text(encoding="utf-8").splitlines()
        for i, h in enumerate(hunks):
            if used >= max_lines_per_file:
                print("TRUNCATED for log limits. Inspect upstream patch for remaining hunks.", flush=True)
                break
            old_line = int(h.group(1))
            endpoint = hunks[i + 1].start() if i + 1 < len(hunks) else len(section)
            diff_lines = section[h.start():endpoint].splitlines()
            # Stop before next binary marker / file header if it follows last hunk.
            diff_lines = [line for line in diff_lines if not line.startswith("diff --git a/")]
            n = min(len(diff_lines), max_lines_per_file - used)
            print(f"-- upstream hunk at original {name}:{old_line} --", flush=True)
            for line in diff_lines[:n]:
                print("PATCH " + line, flush=True)
            used += n
            lo = max(0, old_line - 6)
            hi = min(len(source_lines), old_line + 11)
            print(f"-- Xiaomi source {name}:{lo+1}-{hi} (approximate; not patch anchors) --", flush=True)
            for k in range(lo, hi):
                print(f"BASE {k+1:6}: {source_lines[k]}", flush=True)
        print(f"### END {name}\n", flush=True)
    print("Diagnosis only: DO NOT force patch or disable module ABI protections.", flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("patch", type=Path)
    p.add_argument("kernel_tree", type=Path)
    args = p.parse_args()
    diagnose(args.patch, args.kernel_tree)
