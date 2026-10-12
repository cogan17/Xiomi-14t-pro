#!/usr/bin/env python3
"""Negative source mutations for the pinned shared-credential lifecycle audit.

All mutations live in a temporary directory; no kernel source is changed.
This confirms that the evidence audit detects changes to observed transitions,
not that those transitions are safe or ready for release.
"""
from pathlib import Path
import subprocess
import sys
import tempfile

FILES = (
    "core/init.c",
    "runtime/ksud_integration.c",
    "selinux/selinux.c",
    "selinux/selinux.h",
)
# Label, relative file, unique local anchor, exact string, replacement.
MUTATIONS = (
    ("shared credential preparation removed", "core/init.c",
     "int __init kernelsu_init(void)", "ksu_cred = prepare_creds();", "ksu_cred = NULL;"),
    ("late-load shared credential setup removed", "core/init.c",
     "if (ksu_late_loaded) {", "setup_ksu_cred();", "/* missing setup */"),
    ("late-load local root transition removed", "core/init.c",
     "if (ksu_late_loaded) {", "escape_to_root_for_init();", "/* missing transition */"),
    ("shared credential SELinux failure ignored", "selinux/selinux.c",
     "void setup_ksu_cred(void)", "if (setup_selinux(KERNEL_SU_CONTEXT, ksu_cred))", "if (0)"),
    ("SUSFS second stage stops preparing shared credential", "runtime/ksud_integration.c",
     "int ksu_handle_execveat_ksud(int *fd", "setup_ksu_cred();", "/* missing setup */"),
    ("SUSFS zygote stage stops preparing shared credential", "runtime/ksud_integration.c",
     "static_branch_unlikely(&is_first_zygote)", "setup_ksu_cred();", "/* missing setup */"),
    ("non-SUSFS init second stage setup removed", "runtime/ksud_integration.c",
     "#else\nvoid ksu_handle_execveat_ksud", "setup_ksu_cred();", "/* missing setup */"),
    ("SUSFS startup stage flag not cleared", "runtime/ksud_integration.c",
     "int ksu_handle_execveat_ksud(int *fd", "static_branch_disable(&is_init_second_stage_not_executed);",
     "/* missing disable */"),
    ("module rc overrides different creds", "runtime/ksud_integration.c",
     "static void load_module_rc_once(void)", "override_creds(ksu_cred)", "override_creds(current_cred())"),
    ("module rc fails to restore credentials", "runtime/ksud_integration.c",
     "static void load_module_rc_once(void)", "revert_creds(old_cred);", "/* missing revert */"),
    ("shared credential not released", "core/init.c",
     "void __exit kernelsu_exit(void)", "put_cred(ksu_cred);", "/* missing put */"),
)


def main():
    if len(sys.argv) != 3:
        print("usage: test_rothko_ksun_shared_cred_audit.py KERNEL_ROOT VALIDATOR", file=sys.stderr)
        return 2
    src, validator = Path(sys.argv[1]), Path(sys.argv[2])
    originals = {relative: (src / relative).read_text(encoding="utf-8") for relative in FILES}
    with tempfile.TemporaryDirectory(prefix="rothko-shared-cred-") as temporary:
        root = Path(temporary)
        for relative, data in originals.items():
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(data, encoding="utf-8")

        def run(*flags):
            return subprocess.run(
                [sys.executable, str(validator), str(root), *flags],
                capture_output=True, text=True, timeout=20, check=False
            )

        baseline = run()
        if baseline.returncode or "RELEASE GATE: BLOCKED" not in baseline.stdout or "AUDIT: PASS" not in baseline.stdout:
            raise RuntimeError("baseline evidence audit did not pass with release blocked:\n" +
                               baseline.stdout + baseline.stderr)

        denied = run("--require-reviewed-remediation")
        if denied.returncode != 3 or "REMEDIATION GATE: DENIED" not in denied.stderr:
            raise RuntimeError("known incomplete shared-credential contract was not blocked:\n" +
                               denied.stdout + denied.stderr)
        print("PASS: explicit shared-credential remediation gate remains denied", flush=True)

        for label, relative, anchor, old, new in MUTATIONS:
            original = originals[relative]
            a = original.find(anchor)
            if a < 0:
                raise RuntimeError(f"{label}: missing expected upstream anchor")
            i = original.find(old, a + len(anchor))
            if i < 0:
                raise RuntimeError(f"{label}: missing expected source fragment")
            # Keep mutations within the requested function/config variant.
            if label.startswith("SUSFS") and i > original.find("#else\nvoid ksu_handle_execveat_ksud", a):
                raise RuntimeError(f"{label}: mutation escaped the SUSFS CONFIG branch")
            if label.startswith("non-SUSFS") and i > original.find("#endif\n\nstatic ssize_t", a):
                raise RuntimeError(f"{label}: mutation escaped non-SUSFS CONFIG branch")
            dest = root / relative
            dest.write_text(original[:i] + new + original[i + len(old):], encoding="utf-8")
            result = run()
            dest.write_text(original, encoding="utf-8")
            if result.returncode != 1 or "REVIEW REQUIRED" not in result.stdout:
                raise RuntimeError(f"{label}: validator failed to reject mutation:\n" +
                                   result.stdout + result.stderr)
            print("PASS: rejected source mutation — " + label, flush=True)

    print("PASS: shared-credential negative cases detected; RELEASE REMAINS BLOCKED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
