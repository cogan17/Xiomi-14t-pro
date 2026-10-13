#!/usr/bin/env python3
"""Read-only Rothko BSP source anchors for selective SUSFS porting.

Run against a pristine, explicitly checked-out BSP tree:
  python3 scripts/rothko_susfs_bsp_anchor_map.py /path/to/rothko-bsp

This script does not patch source, download upstream, or decide release safety.
"""
from pathlib import Path
import argparse
import hashlib
import re
import sys

TARGETS = {
    "fs/proc/task_mmu.c": (
        r"\bstruct mem_size_stats\b",
        r"\bstatic void __show_smap\b",
        r"\bstatic int smaps_pte_range\b",
        r"\bvma_pages\s*\(",
        r"\bmemset\s*\(\s*&mss",
    ),
    "mm/memory.c": (
        r"^\s*#include\s*<linux/vmalloc\.h>",
        r"^\s*#include\s*<linux/sched/sysctl\.h>",
        r"^\s*#include\s*<linux/set_memory\.h>",
        r"^\s*#include\s*<trace/events/kmem\.h>",
        r"^\s*#include\s*<trace/hooks/mm\.h>",
    ),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bsp", type=Path, help="Pristine BSP root")
    args = parser.parse_args()
    root = args.bsp.resolve()
    if not (root / "Makefile").is_file():
        print("ERROR: no kernel Makefile; refusing to guess BSP root", file=sys.stderr)
        return 2
    for relative, patterns in TARGETS.items():
        path = root / relative
        if not path.is_file():
            print(f"ERROR: missing {relative}", file=sys.stderr)
            return 2
        raw = path.read_bytes()
        lines = raw.decode("utf-8", errors="replace").splitlines()
        print(f"## {relative} sha256={hashlib.sha256(raw).hexdigest()}")
        for pattern in patterns:
            matches = [
                (number, line.strip())
                for number, line in enumerate(lines, 1)
                if re.search(pattern, line)
            ]
            print(f"  anchor={pattern!r} count={len(matches)}")
            for number, line in matches[:12]:
                print(f"    L{number}: {line[:200]}")
            if len(matches) > 12:
                print(f"    ... {len(matches) - 12} more")
        print("  NOTE: anchor presence is not semantic compatibility or patch approval")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
