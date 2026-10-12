#!/usr/bin/env python3
"""Negative tests for *isolated* G1 status helper candidate.

Source files are copied to a temporary directory. The real pinned checkout
is never changed by these mutations. Integration and release remain blocked.
"""
from pathlib import Path
import subprocess
import sys
import tempfile

PATHS = ("selinux/selinux.c", "selinux/selinux.h",
         "core/init.c", "runtime/ksud_integration.c")
MUTATIONS = (
    ("null check bypass", "selinux/selinux.c",
     "if (!ksu_cred)", "if (false)"),
    ("NULL error overwritten as success", "selinux/selinux.c",
     "return -EINVAL;", "return 0;"),
    ("SELinux error bypass", "selinux/selinux.c",
     "if (ret) {", "if (false) {"),
    ("SELinux error not propagated", "selinux/selinux.c",
     "return ret;", "return 0;"),
    ("domain verification bypass", "selinux/selinux.c",
     "if (!is_task_ksu_domain(ksu_cred)) {", "if (false) {"),
    ("domain error overwritten as success", "selinux/selinux.c",
     "return -EACCES;", "return 0;"),
    ("helper status declaration removed", "selinux/selinux.h",
     "int setup_ksu_cred(void);", "void setup_ksu_cred();"),
)


def main():
    if len(sys.argv) != 3:
        print("usage: test_rothko_ksun_shared_cred_candidate.py KERNEL_ROOT VALIDATOR", file=sys.stderr)
        return 2
    source, validator = Path(sys.argv[1]), Path(sys.argv[2])
    originals = {name: (source / name).read_text(encoding="utf-8") for name in PATHS}
    with tempfile.TemporaryDirectory(prefix="rothko-helper-g1-") as td:
        root = Path(td)
        for rel, data in originals.items():
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(data, encoding="utf-8")

        def audit(*extra):
            return subprocess.run(
                [sys.executable, str(validator), str(root), *extra],
                capture_output=True, text=True, check=False, timeout=20)

        baseline = audit()
        if baseline.returncode or "RELEASE GATE: BLOCKED" not in baseline.stdout:
            raise RuntimeError("baseline must pass source evidence while remaining release-blocked:\n" +
                               baseline.stdout + baseline.stderr)
        denied = audit("--require-integrated")
        if denied.returncode != 3 or "INTEGRATION GATE: DENIED" not in denied.stderr:
            raise RuntimeError("G2–G6 incomplete integration gate was not denied")
        print("PASS: unchanged source candidate remains blocked for integration", flush=True)

        for label, rel, previous, replacement in MUTATIONS:
            contents = originals[rel]
            if rel.endswith("selinux.c"):
                anchor = "int setup_ksu_cred(void)\n{"
                end = "\n}\n\nvoid escape_to_root_for_adb_root"
                first = contents.find(anchor)
                last = contents.find(end, first)
                if first < 0 or last < 0:
                    raise RuntimeError("setup_ksu_cred function boundaries not found")
                pos = contents.find(previous, first + len(anchor), last)
            else:
                pos = contents.find(previous)
            if pos < 0:
                raise RuntimeError(f"{label}: expected mutation source not present")
            dst = root / rel
            dst.write_text(contents[:pos] + replacement + contents[pos + len(previous):],
                           encoding="utf-8")
            result = audit()
            dst.write_text(contents, encoding="utf-8")
            if result.returncode != 1 or "REVIEW REQUIRED" not in result.stdout:
                raise RuntimeError(f"{label}: mutation not detected:\n" + result.stdout + result.stderr)
            print("PASS: detected deliberately weakened G1 helper — " + label, flush=True)
    print("PASS: G1 helper negatives detected; G2–G6 & release STILL BLOCKED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeError, RuntimeError, subprocess.TimeoutExpired) as e:
        print("FAIL: " + str(e), file=sys.stderr)
        raise SystemExit(1)
