#!/usr/bin/env python3
"""Read-only exact-hunk comparator for the pinned SUSFS patch and Rothko BSP.

Usage: python3 scripts/rothko_susfs_hunk_compare.py PATCH BSP_ROOT
No source changes, fuzzing, or patch application.
"""
import argparse
import hashlib
from pathlib import Path
import re
import sys

TARGETS = {"mm/memory.c", "fs/proc/task_mmu.c"}
HEADER = re.compile(r"^@@ -(?P<old>\d+)(?:,(?P<oldcount>\d+))? \+(?P<new>\d+)(?:,(?P<newcount>\d+))? @@")


def parse_patch(lines):
    current = None
    hunks = []
    for line in lines:
        if line.startswith("diff --git a/"):
            name = line.split(" b/", 1)[-1]
            current = name if name in TARGETS else None
        elif current and line.startswith("@@ "):
            match = HEADER.match(line)
            if match:
                hunks.append({"file": current, "header": line, "old": int(match["old"]), "lines": []})
        elif current and hunks and hunks[-1]["file"] == current:
            if line.startswith((" ", "+", "-", "\\")):
                hunks[-1]["lines"].append(line)
    return hunks


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("patch", type=Path)
    ap.add_argument("bsp", type=Path)
    args = ap.parse_args()
    if not args.patch.is_file() or not (args.bsp / "Makefile").is_file():
        print("ERROR: missing patch or BSP kernel Makefile", file=sys.stderr)
        return 2
    hunks = parse_patch(args.patch.read_text(errors="replace").splitlines())
    if not hunks or {h["file"] for h in hunks} != TARGETS:
        print("ERROR: official patch does not contain both expected targets", file=sys.stderr)
        return 2
    for target in sorted(TARGETS):
        path = args.bsp / target
        if not path.is_file():
            print(f"ERROR: missing BSP target {target}", file=sys.stderr)
            return 2
        raw = path.read_bytes()
        src = raw.decode(errors="replace").splitlines()
        print(f"## {target} sha256={hashlib.sha256(raw).hexdigest()}")
        for hunk in [h for h in hunks if h["file"] == target]:
            before = [x[1:] for x in hunk["lines"] if x.startswith((" ", "-"))]
            added = [x[1:] for x in hunk["lines"] if x.startswith("+") and not x.startswith("+++")]
            # Exact old-sequence occurrence only: never claim semantic compatibility.
            matches = [i + 1 for i in range(len(src) - len(before) + 1) if src[i:i + len(before)] == before] if before else []
            anchor = [x[1:] for x in hunk["lines"] if x.startswith(" ") and x[1:].strip()]
            print(f"  {hunk['header']}")
            print(f"    original_lines={len(before)} added_lines={len(added)} exact_old_matches={matches[:8]} total={len(matches)}")
            print(f"    context_lines={len(anchor)} expected_upstream_old_line={hunk['old']}")
            for x in added[:8]:
                print(f"    ADD {x[:180]}")
            if len(added) > 8:
                print(f"    ... {len(added)-8} more additions")
            if len(matches) != 1:
                print("    BLOCK: exact old-sequence match is absent or ambiguous; manual semantic mapping required")
            else:
                print("    NOTE: unique textual match only; NOT an integration approval")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
