#!/usr/bin/env python3
"""Audit the lifetime of shared ksu_cred in pinned KSUN (read-only).

This detects source-pattern drift. PASS means the recorded CURRENT source
contract was inspected; it does not mean the unsafe handoffs were fixed.
The command --require-reviewed-remediation exits nonzero while the known
SELinux/status propagation and consumer-readiness blockers remain.
"""
from pathlib import Path
import argparse
import re
import sys


def block(text: str, left: str, right: str) -> str:
    if text.count(left) != 1:
        raise ValueError(f"missing/duplicate source boundary: {left!r}")
    tail = text.split(left, 1)[1]
    if right not in tail:
        raise ValueError(f"missing source boundary: {right!r}")
    return tail.split(right, 1)[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, help="pinned KSUN kernel/ after sequential candidate patches")
    parser.add_argument("--require-reviewed-remediation", action="store_true",
                        help="must fail while known shared-credential bugs remain; NOT release approval")
    args = parser.parse_args()

    files = {}
    paths = {
        "core": "core/init.c",
        "runtime": "runtime/ksud_integration.c",
        "selinux": "selinux/selinux.c",
        "header": "selinux/selinux.h",
    }
    for label, relative in paths.items():
        files[label] = (args.root / relative).read_text(encoding="utf-8")

    core, runtime, selinux, header = (files[x] for x in ("core", "runtime", "selinux", "header"))
    late = block(core, "if (ksu_late_loaded) {", "\n\t} else {")
    setup = block(selinux, "void setup_ksu_cred(void)\n{", "\n}\n\nvoid escape_to_root_for_adb_root")
    susfs = block(runtime,
                  "#ifdef CONFIG_KSU_SUSFS\nextern int ksu_handle_execveat_init",
                  "#else\nvoid ksu_handle_execveat_ksud")
    nonsusfs = block(runtime,
                     "#else\nvoid ksu_handle_execveat_ksud",
                     "#endif\n\nstatic ssize_t")
    consumer = block(runtime, "static void load_module_rc_once(void)\n{",
                     "\n}\n\nstatic void free_module_rc")
    findings = []

    def check(label: str, ok: bool) -> None:
        print(f"{'PASS' if ok else 'REVIEW REQUIRED'}: {label}", flush=True)
        findings.append(ok)

    check("shared credential allocated and null-checked at KSUN init",
          "ksu_cred = prepare_creds();" in core and
          "if (!ksu_cred) {" in core and
          core.index("ksu_cred = prepare_creds();") < core.index("if (!ksu_cred) {"))
    check("shared credential lifetime ends with put_cred during exit",
          "put_cred(ksu_cred);" in core)
    check("late-load configures shared credential before local root escalation",
          "setup_ksu_cred();" in late and
          "escape_to_root_for_init();" in late and
          late.index("setup_ksu_cred();") < late.index("escape_to_root_for_init();"))
    check("SELinux shared-credential setup failure is logged in candidate",
          "void setup_ksu_cred();" in header and
          "if (setup_selinux(KERNEL_SU_CONTEXT, ksu_cred))" in setup and
          "pr_err(" in setup)
    check("SUSFS second-stage and zygote call shared credential setup",
          susfs.count("setup_ksu_cred();") == 2)
    check("SUSFS stage markers are disabled after shared credential setup",
          susfs.count("static_branch_disable(&is_init_second_stage_not_executed);") == 1 and
          susfs.count("static_branch_disable(&is_first_zygote);") == 1 and
          susfs.index("setup_ksu_cred();") < susfs.index("static_branch_disable(&is_init_second_stage_not_executed);") and
          susfs.rindex("setup_ksu_cred();") < susfs.index("static_branch_disable(&is_first_zygote);"))
    check("non-SUSFS init second-stage also configures shared credential",
          nonsusfs.count("setup_ksu_cred();") == 1 and
          nonsusfs.index("setup_ksu_cred();") < nonsusfs.index("static_branch_disable(&is_init_second_stage_not_executed);"))
    check("module rc loader overrides shared credential and restores previous credential",
          "override_creds(ksu_cred)" in consumer and
          "revert_creds(old_cred);" in consumer and
          consumer.index("override_creds(ksu_cred)") < consumer.index("revert_creds(old_cred);"))
    check("module rc loader uses cleanup label on open error",
          "goto out_revert_creds;" in consumer and
          "out_revert_creds:" in consumer and
          consumer.index("out_revert_creds:") < consumer.index("revert_creds(old_cred);"))

    if not all(findings):
        print("AUDIT: FAILED — source evidence drifted; review upstream and tests.", file=sys.stderr)
        return 1

    # These are observed hazards, not positive security guarantees.
    unsafe_setup = "void setup_ksu_cred(void)" in selinux and "void setup_ksu_cred();" in header
    unchecked_late = "setup_ksu_cred();" in late and "escape_to_root_for_init();" in late
    unchecked_stages = susfs.count("setup_ksu_cred();") == 2
    unchecked_consumer = "override_creds(ksu_cred)" in consumer and not re.search(
        r"if\s*\(\s*!?ksu_cred_(?:ready|valid)\b", consumer)
    print("BLOCK: setup_ksu_cred has void return; no status can propagate to its callers.")
    print("BLOCK: late-load proceeds to root transition without verifying shared-cred setup.")
    print("BLOCK: SUSFS startup clears stage flags without a checked shared-cred setup result.")
    print("BLOCK: module rc reader uses override_creds(ksu_cred) without a verified SELinux-ready contract.")
    print("BLOCK: ownership, concurrency, error unwinding, late-load and module rc read must be reviewed together.")
    print("RELEASE GATE: BLOCKED — no device build, boot, integration, or post-exec session proof.")
    if args.require_reviewed_remediation:
        if unsafe_setup or unchecked_late or unchecked_stages or unchecked_consumer:
            print("REMEDIATION GATE: DENIED — shared credential transition/lifetime not proven.", file=sys.stderr)
            return 3
        # Even a future source refactor cannot imply runtime/kernel approval.
        print("REMEDIATION GATE: REVIEW REQUIRED — evidence changed, run full human audit.", file=sys.stderr)
        return 3
    print("AUDIT: PASS — recorded shared-credential source evidence; release remains BLOCKED.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        print(f"AUDIT: FAILED — {exc}", file=sys.stderr)
        raise SystemExit(1)
