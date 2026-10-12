#!/usr/bin/env python3
"""Read-only G2 late-load/G4 module-rc risk-inventory for pinned KSUN.

This checks exact observed source relationships. A PASS confirms the snapshot,
including its *known hazards*, not a safe rollback, ready credential, or build.
"""
import argparse
from pathlib import Path
import sys


def section(source: str, begin: str, end: str) -> str:
    if source.count(begin) != 1:
        raise ValueError(f"missing/ambiguous section start: {begin!r}")
    after = source.split(begin, 1)[1]
    if end not in after:
        raise ValueError(f"missing section terminator: {end!r}")
    return after.split(end, 1)[0]


def ordered(source: str, *markers: str) -> bool:
    positions = [source.find(marker) for marker in markers]
    return all(i >= 0 for i in positions) and positions == sorted(positions) and len(set(positions)) == len(positions)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("kernel_root", type=Path)
    ap.add_argument("--require-remediation", action="store_true",
                    help="explicitly DENY integration with unresolved G2/G4 readiness")
    args = ap.parse_args()
    core = (args.kernel_root / "core/init.c").read_text(encoding="utf-8")
    rt = (args.kernel_root / "runtime/ksud_integration.c").read_text(encoding="utf-8")

    before_late = section(core, "int __init kernelsu_init(void)\n{", "\n\tif (ksu_late_loaded) {")
    late = section(core, "\tif (ksu_late_loaded) {", "\n\t} else {")
    exit_body = section(core, "void __exit kernelsu_exit(void)\n{", "\n}\n\n#if NEED_OWN_STACKPROTECTOR")
    module_rc = section(rt, "static void load_module_rc_once(void)\n{",
                        "\n}\n\nstatic void free_module_rc")
    rc_hook = section(rt, "static void ksu_install_rc_hook(struct file *file)\n{",
                      "\n}\n\nvoid ksu_handle_sys_read")
    fstat = section(rt, "static long ksu_sys_fstat(const struct pt_regs *regs)\n{",
                    "\n}\n\nstatic int input_handle_event_handler_pre")
    checks = []

    def verify(label: str, ok: bool):
        checks.append(ok)
        print(("PASS" if ok else "REVIEW REQUIRED") + ": " + label, flush=True)

    verify("G2 shared credentials allocated before registration",
           ordered(before_late, "ksu_cred = prepare_creds();",
                   "ksu_init_symbol_resolver();", "ksu_feature_init();"))
    verify("G2 core feature/log/adb hooks initialized before late-load setup",
           ordered(before_late, "ksu_feature_init();", "ksu_sulog_init();",
                   "ksu_adb_root_init();", "ksu_selinux_hide_init();",
                   "ksu_supercalls_init();", "ksu_app_profile_init();"))
    verify("G2 SUSFS-specific hooks registered before late-load setup",
           ordered(before_late, "ksu_sucompat_init();",
                   "ksu_setuid_hook_init();", "ksu_avc_spoof_init();"))
    verify("G2 late-load applies policy, sets shared context, then attempts root",
           ordered(late, "apply_kernelsu_rules();", "cache_sid();",
                   "setup_ksu_cred();", "escape_to_root_for_init();",
                   "ksu_allowlist_init();"))
    verify("G2 late-load can declare boot complete after unchecked setup calls",
           ordered(late, "setup_ksu_cred();", "escape_to_root_for_init();",
                   "ksu_boot_completed = true;"))
    verify("G2 exit stops supercalls then waits for RCU readers",
           ordered(exit_body, "ksu_supercalls_exit();", "synchronize_rcu();",
                   "ksu_observer_exit();"))
    verify("G2 exit includes SUSFS hook cleanup and SELinux hide exit",
           ordered(exit_body, "ksu_avc_spoof_exit();", "ksu_sucompat_exit();",
                   "ksu_setuid_hook_exit();", "ksu_selinux_hide_exit();"))
    verify("G2 exit releases core features and shared credential",
           ordered(exit_body, "ksu_adb_root_exit();", "ksu_sulog_exit();",
                   "ksu_feature_exit();", "put_cred(ksu_cred);"))
    verify("G4 module rc one-shot loaded flag precedes override",
           ordered(module_rc, "if (loaded)", "loaded = true;", "if (ksu_no_custom_rc)",
                   "override_creds(ksu_cred)", "open_module_rc(&path)"))
    verify("G4 module rc has no verified credential-readiness check before override",
           "is_task_ksu_domain(ksu_cred)" not in module_rc and
           "ksu_cred_ready" not in module_rc and
           "override_creds(ksu_cred)" in module_rc)
    verify("G4 module rc preserves cleanup of any successful override",
           ordered(module_rc, "old_cred = override_creds(ksu_cred);",
                   "out_revert_creds:", "revert_creds(old_cred);"))
    verify("G4 module rc publishes module length after successful read",
           ordered(module_rc, "r = kernel_read(", "module_rc_len = r;"))
    verify("G4 init rc hook is disabled before module rc loading",
           ordered(rc_hook, "rc_hooked = true;", "stop_init_rc_hook();",
                   "load_module_rc_once();"))
    verify("G4 SUSFS init rc hook likewise clears static key before loader",
           ordered(rc_hook, "rc_hooked = true;",
                   "static_branch_disable(&ksu_is_init_rc_hook_enabled);",
                   "load_module_rc_once();"))
    verify("G4 non-SUSFS fstat path calls same one-shot loader",
           ordered(fstat, "if (is_init_rc(file)) {",
                   "load_module_rc_once();", "fput(file);"))

    print("BLOCK: G2 late-load can fail after hook registration; no proven reverse-order unwind.")
    print("BLOCK: module exit sequence is NOT an init-failure cleanup contract.")
    print("BLOCK: G4 loaded/rc_hooked and hook disable precede credential readiness.")
    print("BLOCK: moving a readiness check alone can irreversibly lose init.rc/module-rc handling.")
    print("BLOCK: G3 repeated startup work, G5 credential ownership, FD session, KMI and boot remain open.")
    print("RELEASE GATE: BLOCKED — this is source-risk evidence only.")
    if not all(checks):
        print("AUDIT: FAILED — pinned G2/G4 source inventory drifted.", file=sys.stderr)
        return 1
    if args.require_remediation:
        print("REMEDIATION GATE: DENIED — G2 unwind and G4 latch/ready contract are unresolved.", file=sys.stderr)
        return 3
    print("AUDIT: PASS — known G2/G4 hazards mapped; release remains BLOCKED.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, UnicodeError) as e:
        print("AUDIT: FAILED — " + str(e), file=sys.stderr)
        raise SystemExit(1)
