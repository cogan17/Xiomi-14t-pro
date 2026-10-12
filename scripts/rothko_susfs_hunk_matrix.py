#!/usr/bin/env python3
"""Read-only exact-context compatibility matrix for a pinned SUSFS kernel patch.

Each unified-diff hunk is checked independently using git apply --check.
A passing hunk is NOT proof that a complete or semantically correct port exists:
hunks can depend on changes from earlier hunks. Zero source files are changed.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import subprocess
import sys

DIFF_START = re.compile(r"(?m)^diff --git a/(.+?) b/([^\n]+)\n")
HUNK_START = re.compile(r"(?m)^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def patch_sections(content: str):
    matches = list(DIFF_START.finditer(content))
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        section = content[match.start():end]
        hunks = list(HUNK_START.finditer(section))
        if not hunks:
            continue
        header = section[:hunks[0].start()]
        # File headers are required to prevent unsafe path ambiguity.
        if not header.startswith("diff --git a/") or "\n+++ b/" not in header:
            raise ValueError("Malformed Git diff header: " + match.group(1))
        yield match.group(1), header, section, hunks


def diagnose(kernel_tree: Path, patch_path: Path, output_limit: int = 1000):
    patch = patch_path.read_text(encoding="utf-8")
    total = passed = failed = 0
    summary = ["| Source | Isolated exact hunks passing | Failing hunk positions |",
               "|---|---:|---|"]
    for filename, header, section, hunks in patch_sections(patch):
        if filename.startswith("/") or ".." in Path(filename).parts:
            raise ValueError("Invalid patch path: " + filename)
        good = []
        bad = []
        for idx, hunk in enumerate(hunks):
            end = hunks[idx + 1].start() if idx + 1 < len(hunks) else len(section)
            single = header + section[hunk.start():end]
            result = subprocess.run(
                ["git", "-C", str(kernel_tree), "apply", "--check", "--whitespace=error", "-"],
                input=single, text=True, capture_output=True, check=False, timeout=20,
            )
            # Passing independently is a diagnostic only, not a replacement for full patch.
            total += 1
            if result.returncode == 0:
                passed += 1
                good.append(hunk.group(1))
            else:
                failed += 1
                bad.append(hunk.group(1))
        marker = ", ".join("L" + s for s in bad[:35]) or "—"
        print(f"{filename}: independent hunks {len(good)}/{len(hunks)} match; mismatch at {marker}", flush=True)
        summary.append(f"| {filename} | {len(good)}/{len(hunks)} | {marker} |")
    summary.append(f"\n**Total isolated checks: {passed}/{total} pass; {failed} fail.**")
    summary.append("Isolated hunk results are advisory; FULL git apply --check remains mandatory.")
    summary.append("No partial patch applied, no unchecked hunk dropped, no flashable artifact.")
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write("\n### SUSFS 6.1 Xiaomi BSP exact-hunk compatibility (diagnostic)\n\n")
            f.write("\n".join(summary) + "\n")
    print("\n".join(summary), flush=True)
    return failed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kernel_tree", type=Path)
    parser.add_argument("upstream_patch", type=Path)
    args = parser.parse_args()
    if not (args.kernel_tree / "Makefile").is_file() or not args.upstream_patch.is_file():
        parser.error("Expected kernel Makefile and an upstream patch")
    # Preserve original non-zero status of strict-apply failure; this report is not the gate.
    diagnose(args.kernel_tree, args.upstream_patch)
