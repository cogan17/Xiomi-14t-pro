#!/usr/bin/env python3
"""Source-only G3 startup caller-guard candidate audit on pinned KSUN.

PASS: expected checked status and stage-key ordering is observed.
BLOCKED: retry side effects, concurrency, G2/G4/G5, FD, kernel runtime unproven.
"""
import argparse
from pathlib import Path
import re
import sys

KEYS = ("is_init_second_stage_not_executed", "is_first_zygote")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("kernel_root", type=Path)
    p.add_argument("--require-safe-retry", action="store_true",
                   help="always denied pending review of reentrant startup side effects")
    args = p.parse_args()
    src = (args.kernel_root / "runtime/ksud_integration.c").read_text(encoding="utf-8")
    start = "#ifdef CONFIG_KSU_SUSFS\nextern int ksu_handle_execveat_init"
    middle = "#else\nvoid ksu_handle_execveat_ksud"
    end = "#endif\n\nstatic ssize_t"
    if any(src.count(x) != 1 for x in (start, middle, end)):
        raise ValueError("pinned startup CONFIG/function boundaries changed")
    susfs = src.split(start, 1)[1].split(middle, 1)[0]
    nonsusfs = src.split(middle, 1)[1].split(end, 1)[0]
    checks = []

    def check(label, ok):
        checks.append(ok)
        print(("PASS" if ok else "REVIEW REQUIRED") + ": " + label, flush=True)

    cases = [
        ("SUSFS second stage", susfs, "is_init_second_stage_not_executed", "return 0;"),
        ("SUSFS first zygote", susfs, "is_first_zygote", "return 0;"),
        ("non-SUSFS second stage", nonsusfs, "is_init_second_stage_not_executed", "return;"),
    ]
    for label, branch, key, expected_return in cases:
        # A deliberately narrow check. No source control-flow proof is claimed.
        pattern = (
            r"if\s*\(\s*setup_ksu_cred\(\)\s*\)\s*\{\s*"
            r"pr_err\([^\n]*\);\s*"
            + re.escape(expected_return) +
            r"\s*\}\s*static_branch_disable\(&" + re.escape(key) + r"\);"
        )
        matches = list(re.finditer(pattern, branch))
        check(label + ": error exits before clearing one-shot key", len(matches) == 1)
        check(label + ": legacy unchecked helper invocation absent", (
            not re.search(r"(?<!if \()setup_ksu_cred\(\);", branch)
            and branch.count("if (setup_ksu_cred()) {") ==
            (2 if branch is susfs else 1)
        ))
    check("non-SUSFS zygote has a distinct stop-hook path",
          "ksu_stop_ksud_execve_hook();" in nonsusfs and
          "static_branch_disable(&is_first_zygote);" in nonsusfs)
    check("SUSFS zygote still performs post-fs-data before shared cred verification",
          "on_post_fs_data();" in susfs and
          susfs.index("on_post_fs_data();") < susfs.index("if (setup_ksu_cred()) {", susfs.index("on_post_fs_data();")))
    check("SUSFS second stage still performs mutable work before checked setup",
          "apply_kernelsu_rules();" in susfs and
          susfs.index("apply_kernelsu_rules();") < susfs.index("if (setup_ksu_cred()) {"))

    print("BLOCK: a failed check leaves a one-shot key pending: retry frequency/idempotence unresolved.")
    print("BLOCK: SUSFS on_post_fs_data/apply_kernelsu_rules may repeat before readiness.")
    print("BLOCK: no validated response to SELinux failure for later module rc consumers.")
    print("BLOCK: G2 late-load unwind, G4/G5 shared-cred ownership, post-exec FD and ABI unverified.")
    print("RELEASE GATE: BLOCKED — source-only candidate, not a safe runtime retry strategy.")
    if not all(checks):
        print("AUDIT: FAILED — startup candidate source structure drifted.", file=sys.stderr)
        return 1
    if args.require_safe_retry:
        print("RETRY GATE: DENIED — idempotence and boundedness not proven.", file=sys.stderr)
        return 3
    print("AUDIT: PASS — three candidate caller guards observed, RELEASE BLOCKED.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, UnicodeError) as error:
        print("AUDIT: FAILED — " + str(error), file=sys.stderr)
        raise SystemExit(1)
