#!/usr/bin/env python3
"""Negative tests that ensure the pinned KSUN ioctl permissions cannot drift.

Runs on a temporary copy of only dispatch.c and perm.c. Never patches
the actual source checkout, builds a kernel, or grants privileges.
"""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

MUTATIONS = (
    # label, relative source, unique section anchor, original text, replacement
    ("grant root becomes public", "supercall/dispatch.c", ".cmd = KSU_IOCTL_GRANT_ROOT",
     ".perm_check = allowed_for_su", ".perm_check = always_allow"),
    ("SELinux policy accessible to anyone", "supercall/dispatch.c", ".cmd = KSU_IOCTL_SET_SEPOLICY",
     ".perm_check = only_root", ".perm_check = always_allow"),
    ("profile update accessible to root", "supercall/dispatch.c", ".cmd = KSU_IOCTL_SET_APP_PROFILE",
     ".perm_check = only_manager", ".perm_check = manager_or_root"),
    ("feature update becomes public", "supercall/dispatch.c", ".cmd = KSU_IOCTL_SET_FEATURE",
     ".perm_check = manager_or_root", ".perm_check = always_allow"),
    ("sulog fd accessible to any manager", "supercall/dispatch.c", ".cmd = KSU_IOCTL_GET_SULOG_FD",
     ".perm_check = only_root", ".perm_check = manager_or_root"),
    ("wrapper fd class unexpectedly changed", "supercall/dispatch.c", ".cmd = KSU_IOCTL_GET_WRAPPER_FD",
     ".perm_check = manager_or_root", ".perm_check = only_root"),
    ("public GET_INFO restricted unexpectedly", "supercall/dispatch.c", ".cmd = KSU_IOCTL_GET_INFO,",
     ".perm_check = always_allow", ".perm_check = only_root"),
    ("grant helper unconditional", "supercall/perm.c", "bool allowed_for_su(void)",
     "return is_manager() || ksu_is_allow_uid_for_current(current_uid().val);", "return true;"),
    ("root helper unconditional", "supercall/perm.c", "bool only_root(void)",
     "return current_uid().val == 0;", "return true;"),
    ("manager-or-root helper unconditional", "supercall/perm.c", "bool manager_or_root(void)",
     "return current_uid().val == 0 || is_manager();", "return true;"),
    ("dispatcher guard disabled", "supercall/dispatch.c", "long ksu_supercall_handle_ioctl(",
     "ksu_ioctl_handlers[i].perm_check && !ksu_ioctl_handlers[i].perm_check()", "false"),
    ("unknown command appended", "supercall/dispatch.c", ".cmd = 0,",
     ".cmd = 0,", ".cmd = KSU_IOCTL_UNREVIEWED,"),
)


def main():
    if len(sys.argv) != 3:
        print("usage: test_rothko_ksun_ioctl_matrix.py KERNEL_SOURCE_ROOT VALIDATOR", file=sys.stderr)
        return 2
    src = Path(sys.argv[1])
    validator = Path(sys.argv[2])
    if not validator.is_file():
        raise RuntimeError(f"missing validator: {validator}")
    originals = {
        relative: (src / relative).read_text(encoding="utf-8")
        for relative in ("supercall/dispatch.c", "supercall/perm.c")
    }

    with tempfile.TemporaryDirectory(prefix="rothko-ioctl-matrix-") as td:
        root = Path(td)
        for relative, contents in originals.items():
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(contents, encoding="utf-8")

        def audit():
            return subprocess.run([sys.executable, str(validator), str(root)],
                                  capture_output=True, text=True, check=False, timeout=20)

        baseline = audit()
        if baseline.returncode or "RELEASE GATE: BLOCKED" not in baseline.stdout:
            raise RuntimeError("baseline audit not a success with release blocked:\n"
                               + baseline.stdout + baseline.stderr)
        for label, relative, anchor, old, new in MUTATIONS:
            original = originals[relative]
            pos_anchor = original.find(anchor)
            if pos_anchor < 0:
                raise RuntimeError(f"{label}: expected anchor missing")
            pos = original.find(old, pos_anchor)
            if pos < 0:
                raise RuntimeError(f"{label}: expected original text missing")
            # A command entry must be mutated within its own brace-delimited
            # table row; do not silently patch the next unrelated row.
            if anchor.startswith(".cmd = KSU_IOCTL_"):
                row_end = original.find("}", pos_anchor)
                if pos >= row_end:
                    raise RuntimeError(f"{label}: mutation target belongs to another command")
            target = root / relative
            target.write_text(original[:pos] + new + original[pos + len(old):], encoding="utf-8")
            result = audit()
            target.write_text(original, encoding="utf-8")
            if result.returncode == 0 or "AUDIT: FAILED" not in result.stderr:
                raise RuntimeError(f"unsafe permission change was not rejected: {label}\n"
                                   + result.stdout + result.stderr)
            print("PASS: rejected permission drift — " + label, flush=True)

    print("PASS: all ioctl matrix mutations detected; RELEASE REMAINS BLOCKED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeError, subprocess.TimeoutExpired, RuntimeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
