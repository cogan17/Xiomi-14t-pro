#!/usr/bin/env python3
"""Negative mutation sensitivity for the pinned G2/G4 risk inventory.

Tests that removals/reordering of observed hazard-related source statements
do not silently produce an audit PASS. Each test mutates TEMPORARY copies;
none establishes complete kernel safety or remediation.
"""
from pathlib import Path
import subprocess
import sys
import tempfile

FILES = ("core/init.c", "runtime/ksud_integration.c")
# label, file, source section, old token, replacement
MUTATIONS = (
    ("G2 cred allocation removed", "core/init.c", "pre", "ksu_cred = prepare_creds();", "ksu_cred = NULL;"),
    ("G2 early feature setup removed", "core/init.c", "pre", "ksu_feature_init();", "/* no feature */"),
    ("G2 adb root setup removed", "core/init.c", "pre", "ksu_adb_root_init();", "/* no adb hook */"),
    ("G2 early supercall registration removed", "core/init.c", "pre", "ksu_supercalls_init();", "/* no supercalls */"),
    ("G2 SUSFS hook registration removed", "core/init.c", "pre", "ksu_sucompat_init();", "/* no sucompat */"),
    ("G2 setuid hook registration removed", "core/init.c", "pre", "ksu_setuid_hook_init();", "/* no setuid */"),
    ("G2 late-load SELinux setup skipped", "core/init.c", "late", "setup_ksu_cred();", "/* no setup */"),
    ("G2 late-load root request skipped", "core/init.c", "late", "escape_to_root_for_init();", "/* no privilege attempt */"),
    ("G2 boot-ready latch no longer observable", "core/init.c", "late", "ksu_boot_completed = true;", "/* no latch */"),
    ("G2 RCU synchronization removed", "core/init.c", "exit", "synchronize_rcu();", "/* no RCU wait */"),
    ("G2 supercalls exit removed", "core/init.c", "exit", "ksu_supercalls_exit();", "/* no shutdown */"),
    ("G2 SUSFS teardown removed", "core/init.c", "exit", "ksu_sucompat_exit();", "/* no SUSFS teardown */"),
    ("G2 shared cred release removed", "core/init.c", "exit", "put_cred(ksu_cred);", "/* no release */"),
    ("G4 early loaded latch removed", "runtime/ksud_integration.c", "module", "loaded = true;", "/* no latch */"),
    ("G4 unguarded override changed", "runtime/ksud_integration.c", "module", "override_creds(ksu_cred)", "override_creds(current_cred())"),
    ("G4 cleanup return credentials removed", "runtime/ksud_integration.c", "module", "revert_creds(old_cred);", "/* no revert */"),
    ("G4 successful module length removed", "runtime/ksud_integration.c", "module", "module_rc_len = r;", "/* no payload length */"),
    ("G4 init rc latch removed", "runtime/ksud_integration.c", "hook", "rc_hooked = true;", "/* no rc latch */"),
    ("G4 early stop hook removed", "runtime/ksud_integration.c", "hook", "stop_init_rc_hook();", "/* no hook stop */"),
    ("G4 SUSFS static key stop removed", "runtime/ksud_integration.c", "hook", "static_branch_disable(&ksu_is_init_rc_hook_enabled);", "/* no static key stop */"),
    ("G4 fstat loader call removed", "runtime/ksud_integration.c", "fstat", "load_module_rc_once();", "/* no fstat loader */"),
)


def bounds(text: str, key: str) -> tuple[int, int]:
    lookup = {
        "pre": ("int __init kernelsu_init(void)\n{", "\n\tif (ksu_late_loaded) {"),
        "late": ("\tif (ksu_late_loaded) {", "\n\t} else {"),
        "exit": ("void __exit kernelsu_exit(void)\n{", "\n}\n\n#if NEED_OWN_STACKPROTECTOR"),
        "module": ("static void load_module_rc_once(void)\n{", "\n}\n\nstatic void free_module_rc"),
        "hook": ("static void ksu_install_rc_hook(struct file *file)\n{", "\n}\n\nvoid ksu_handle_sys_read"),
        "fstat": ("static long ksu_sys_fstat(const struct pt_regs *regs)\n{",
                  "\n}\n\nstatic int input_handle_event_handler_pre"),
    }
    start, end = lookup[key]
    if text.count(start) != 1:
        raise RuntimeError(f"{key}: ambiguous start marker")
    lo = text.index(start) + len(start)
    hi = text.find(end, lo)
    if hi < 0:
        raise RuntimeError(f"{key}: missing end marker")
    return lo, hi


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: test_rothko_ksun_g2_g4_risk_audit.py KERNEL_ROOT AUDITOR", file=sys.stderr)
        return 2
    root, audit_path = Path(sys.argv[1]), Path(sys.argv[2])
    originals = {name: (root / name).read_text(encoding="utf-8") for name in FILES}
    with tempfile.TemporaryDirectory(prefix="rothko-g2-g4-") as tmp:
        temp_root = Path(tmp)
        for rel, data in originals.items():
            out = temp_root / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(data, encoding="utf-8")

        def audit(*flags):
            return subprocess.run(
                [sys.executable, str(audit_path), str(temp_root), *flags],
                capture_output=True, text=True, timeout=20, check=False
            )

        baseline = audit()
        if baseline.returncode or "RELEASE GATE: BLOCKED" not in baseline.stdout:
            raise RuntimeError("risk inventory baseline must PASS but keep release blocked:\n"
                               + baseline.stdout + baseline.stderr)
        gate = audit("--require-remediation")
        if gate.returncode != 3 or "REMEDIATION GATE: DENIED" not in gate.stderr:
            raise RuntimeError("G2/G4 remediation gate was not explicitly denied")
        print("PASS: G2/G4 remediation gate explicitly DENIED", flush=True)

        for label, rel, scope, old, replacement in MUTATIONS:
            data = originals[rel]
            lo, hi = bounds(data, scope)
            pos = data.find(old, lo, hi)
            if pos < 0:
                raise RuntimeError(f"{label}: expected source token absent inside {scope}")
            changed = data[:pos] + replacement + data[pos + len(old):]
            temp_path = temp_root / rel
            temp_path.write_text(changed, encoding="utf-8")
            result = audit()
            temp_path.write_text(data, encoding="utf-8")
            if result.returncode != 1 or "REVIEW REQUIRED" not in result.stdout:
                raise RuntimeError(f"{label}: unrecognized source mutation:\n"
                                   + result.stdout + result.stderr)
            print("PASS: auditor detects changed source — " + label, flush=True)

    print("PASS: all 21 G2/G4 risk-inventory mutations detected; RELEASE BLOCKED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeError, RuntimeError, subprocess.TimeoutExpired) as e:
        print("FAIL: " + str(e), file=sys.stderr)
        raise SystemExit(1)
