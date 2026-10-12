#!/usr/bin/env python3
"""Strict five-hunk context adaptation for Simonpunk SUSFS and Xiaomi BSP 6.1.57.

This tool updates ONLY diff context lines at exact audited hunk positions.
It NEVER removes or rewrites any upstream added/removed C code, never applies
the patch, and rejects unexpected upstream or vendor context. The full result
must still pass git apply --check --whitespace=error before being applied.
"""
import argparse
from pathlib import Path
import re
import sys

HUNK_RE = re.compile(
    r"^@@ -(?P<old>\d+)(?:,(?P<oc>\d+))? "
    r"\+(?P<new>\d+)(?:,(?P<nc>\d+))? @@(?P<suffix>.*)$"
)
FILE_RE = re.compile(r"^diff --git a/(.+) b/(.+)$")

# The only five mismatches confirmed by diagnostic workflow #38210272383.
# Context lines begin with one literal space; none are additions/deletions.
FIXES = {
    ("fs/exec.c", 64): (
        [(" #ifndef __GENKSYMS__", " #include <linux/uaccess.h>"),
         (" #include <linux/dma-buf.h>", " #include <asm/mmu_context.h>")],
        "static int bprm_creds_from_file(",
    ),
    ("fs/namei.c", 1614): (
        [(" EXPORT_SYMBOL(lookup_one_qstr_excl);", " ")],
        "static struct dentry *__lookup_hash(",
    ),
    ("fs/proc/base.c", 100): (
        [(" #include <linux/dma-buf.h>", None)],
        "#include <trace/hooks/sched.h>",
    ),
    ("fs/proc/task_mmu.c", 883): (
        [(" \tif (!vma_pages(vma))", " \tsmap_gather_stats(vma, &mss, 0);")],
        "trace_android_vh_show_smap(",
    ),
    ("mm/memory.c", 79): (
        [(" #include <trace/hooks/mm.h>", None)],
        "#include <asm/mmu_context.h>",
    ),
}


def body_counts(lines):
    old = sum(1 for s in lines if s.startswith((" ", "-")))
    new = sum(1 for s in lines if s.startswith((" ", "+")))
    return old, new


def adapt(text: str, kernel_tree: Path) -> str:
    lines = text.splitlines(keepends=True)
    result = []
    path = None
    found = set()
    i = 0
    original_operations = [s for s in lines if s.startswith(("+", "-"))]
    while i < len(lines):
        file_match = FILE_RE.match(lines[i].rstrip("\n"))
        if file_match:
            if file_match.group(1) != file_match.group(2):
                raise ValueError("Unexpected rename patch: " + lines[i])
            path = file_match.group(1)
            result.append(lines[i])
            i += 1
            continue
        header_match = HUNK_RE.match(lines[i].rstrip("\n"))
        if not header_match or path is None:
            result.append(lines[i])
            i += 1
            continue
        header = lines[i]
        i += 1
        body = []
        while i < len(lines) and not HUNK_RE.match(lines[i]) and not FILE_RE.match(lines[i]):
            if lines[i] and lines[i][0] not in (" ", "+", "-", "\\"):
                raise ValueError("Unexpected text in unified diff hunk")
            body.append(lines[i])
            i += 1
        old_count, new_count = body_counts(body)
        if old_count != int(header_match.group("oc") or 1) or \
           new_count != int(header_match.group("nc") or 1):
            raise ValueError(f"Malformed upstream diff hunk for {path}")
        key = (path, int(header_match.group("old")))
        if key not in FIXES:
            result.append(header)
            result.extend(body)
            continue
        if key in found:
            raise ValueError(f"Duplicate upstream hunk: {key}")
        replacements, vendor_anchor = FIXES[key]
        source = kernel_tree / path
        if not source.is_file() or vendor_anchor not in source.read_text(encoding="utf-8"):
            raise ValueError(f"Unaudited Xiaomi source context for {path}")
        updated = body.copy()
        for src, replacement in replacements:
            occurrences = [ix for ix, line in enumerate(updated) if line.rstrip("\n") == src]
            if len(occurrences) != 1:
                raise ValueError(f"Expected exactly one '{src}' in upstream hunk {key}")
            at = occurrences[0]
            if replacement is None:
                updated.pop(at)
            else:
                updated[at] = replacement + "\n"
        if [v for v in body if v.startswith(("+", "-"))] != \
           [v for v in updated if v.startswith(("+", "-"))]:
            raise ValueError(f"Kernel changes were modified while porting {path}")
        new_old_count, new_new_count = body_counts(updated)
        suffix = header_match.group("suffix")
        # Original line numbers are hints; git apply enforces exact context.
        new_header = (
            f"@@ -{header_match.group('old')},{new_old_count}"
            f" +{header_match.group('new')},{new_new_count} @@{suffix}\n"
        )
        result.append(new_header)
        result.extend(updated)
        found.add(key)
    if found != set(FIXES):
        raise ValueError("Expected exactly five audited context fixes, got " + repr(found))
    output = "".join(result)
    if [s for s in output.splitlines(keepends=True) if s.startswith(("+", "-"))] != original_operations:
        raise ValueError("Upstream '+'/'-' lines differ after adaptation")
    if output == text:
        raise ValueError("No context changes were performed")
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream-patch", type=Path, required=True)
    parser.add_argument("--tree", type=Path, required=True)
    parser.add_argument("--output-patch", type=Path, required=True)
    args = parser.parse_args()
    if args.output_patch.exists():
        parser.error("Refusing to overwrite existing adapted patch")
    if not (args.tree / "build.config.common").is_file():
        parser.error("Invalid Xiaomi BSP source tree")
    output = adapt(args.upstream_patch.read_text(encoding="utf-8"), args.tree)
    args.output_patch.write_text(output, encoding="utf-8")
    print("Prepared five context-only updates; all upstream added/deleted lines preserved.")
    print("Next: full git apply --check --whitespace=error remains MANDATORY.")


if __name__ == "__main__":
    main()
