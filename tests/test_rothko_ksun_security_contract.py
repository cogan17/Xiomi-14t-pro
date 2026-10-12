#!/usr/bin/env python3
"""Negative regression tests for the read-only, pinned-KSUN source audit.

Runs only against a temporary copy of eight small source files after CI has
already applied the four candidate patches to its ephemeral checkout.
No kernel build, write to upstream, GitLab access, artifact, or flash.
"""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

FILES = (
    "feature/sucompat.c",
    "policy/app_profile.c",
    "supercall/perm.c",
    "supercall/dispatch.c",
    "supercall/supercall.c",
    "selinux/selinux.c",
    "selinux/selinux.h",
    "hook/syscall_event_bridge.c",
)

# (scenario, source file, anchor within file, exact old text, replacement)
MUTATIONS = (
    ("su uid allowlist removed", "feature/sucompat.c",
     "int ksu_handle_execveat_sucompat(int *fd",
     "if (!ksu_is_allow_uid_for_current(current_uid().val))", "if (0)"),
    ("su chroot guard removed", "feature/sucompat.c",
     "int ksu_handle_execveat_sucompat(int *fd",
     "if (current_chrooted())", "if (0)"),
    ("su filename redirect removed", "feature/sucompat.c",
     "int ksu_handle_execveat_sucompat(int *fd",
     "*filename_ptr = replacement;", "/* deliberately removed */"),
    ("GRANT_ROOT permission bypass", "supercall/dispatch.c",
     ".cmd = KSU_IOCTL_GRANT_ROOT",
     ".perm_check = allowed_for_su", ".perm_check = always_allow"),
    ("ioctl permission check bypass", "supercall/dispatch.c",
     "long ksu_supercall_handle_ioctl(",
     "ksu_ioctl_handlers[i].perm_check()", "false"),
    ("root profile SELinux result ignored", "policy/app_profile.c",
     "int escape_with_root_profile(void)",
     "ret = setup_selinux(profile->selinux_domain, cred);",
     "setup_selinux(profile->selinux_domain, cred);"),
    ("init SELinux failure ignored", "policy/app_profile.c",
     "int escape_to_root_for_init(void)",
     "if (setup_selinux(KERNEL_SU_CONTEXT, cred)) {", "if (0) {"),
    ("driver fd CLOEXEC disabled", "supercall/supercall.c",
     "int ksu_install_fd(void)",
     "get_unused_fd_flags(O_CLOEXEC)", "get_unused_fd_flags(0)"),
    ("ksu_cred SELinux failure no longer observed", "selinux/selinux.c",
     "void setup_ksu_cred(void)",
     "if (setup_selinux(KERNEL_SU_CONTEXT, ksu_cred))",
     "if (false)"),
)


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: test_rothko_ksun_security_contract.py PINNED_PATCHED_KERNEL_ROOT AUDIT_SCRIPT", file=sys.stderr)
        return 2
    source_root, validator = Path(sys.argv[1]), Path(sys.argv[2])
    if not validator.is_file():
        raise RuntimeError(f"validator is missing: {validator}")

    with tempfile.TemporaryDirectory(prefix="rothko-source-contract-") as d:
        root = Path(d)
        originals = {}
        for relative in FILES:
            src = source_root / relative
            if not src.is_file():
                raise RuntimeError(f"required pinned source not found: {src}")
            dest = root / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)
            originals[relative] = src.read_text(encoding="utf-8")

        def audit():
            return subprocess.run(
                [sys.executable, str(validator), str(root)],
                capture_output=True, text=True, timeout=20, check=False,
            )

        baseline = audit()
        if baseline.returncode or "AUDIT: PASS" not in baseline.stdout or "RELEASE GATE: BLOCKED" not in baseline.stdout:
            raise RuntimeError("baseline patched source did not pass the structural audit (with release still blocked):\n"
                               + baseline.stdout + baseline.stderr)

        for label, relative, anchor, old, new in MUTATIONS:
            original = originals[relative]
            anchor_index = original.find(anchor)
            if anchor_index < 0:
                raise RuntimeError(f"{label}: anchor missing; review pinned upstream changes")
            position = original.find(old, anchor_index + len(anchor))
            if position < 0:
                raise RuntimeError(f"{label}: expected pattern missing after anchor")
            mutated = original[:position] + new + original[position + len(old):]
            dest = root / relative
            dest.write_text(mutated, encoding="utf-8")
            result = audit()
            dest.write_text(original, encoding="utf-8")
            if result.returncode == 0 or "REVIEW REQUIRED" not in result.stdout:
                raise RuntimeError(f"false PASS for mutation '{label}':\n"
                                   + result.stdout + result.stderr)
            print("PASS: validator rejected injected failure — " + label, flush=True)

        print("PASS: all negative mutation checks rejected; RELEASE STILL BLOCKED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print("FAIL: " + str(exc), file=sys.stderr)
        raise SystemExit(1)
