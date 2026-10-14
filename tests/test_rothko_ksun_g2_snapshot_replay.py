#!/usr/bin/env python3
"""Focused G2 snapshot/replay composition; no rollback or runtime proof."""
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from test_rothko_ksun_escape_precommit import NAMES as BASE_NAMES
from test_rothko_ksun_g5_composition import PIN, body, git, ordered, require

NAME = "g2-snapshot-replay-composable"
NAMES = BASE_NAMES + (NAME,)
CHANGED = {"kernel/selinux/rules.c", "kernel/runtime/ksud_integration.c"}


def contract(src):
    rules = body(src["kernel/selinux/rules.c"], "int apply_kernelsu_rules(void)")
    lock = "mutex_lock(&selinux_state.policy_mutex);"
    require("selinux_state.policy" not in rules.split(lock, 1)[0],
            "no unlocked policy snapshot")
    ordered(rules, "static bool policy_attempted;", lock, "if (policy_attempted) {",
            "ret = -EALREADY;", "goto out_unlock;", "policy_attempted = true;",
            "old_pol = rcu_dereference_protected(selinux_state.policy,",
            "lockdep_is_held(&selinux_state.policy_mutex)", "if (!old_pol) {",
            "ret = -EAGAIN;", "goto out_unlock;", "backup_sepolicy =",
            "ksu_dup_sepolicy(", "if (!backup_sepolicy)", "goto out_unlock;",
            "pol = ksu_dup_sepolicy(", "rcu_assign_pointer(selinux_state.policy, pol);",
            "synchronize_rcu();", "ksu_destroy_sepolicy(old_pol);", "reset_avc_cache();",
            "out_unlock:", "mutex_unlock(&selinux_state.policy_mutex);", "return ret;")
    require(rules.count("policy_attempted = true;") == 1, "one policy attempt latch")
    require(not re.search(r"policy_attempted\s*=\s*(?:false|0)\s*;", rules),
            "policy failures must not reset the latch")
    require(rules.count("old_pol =") == 1, "single snapshot")
    require(rules.count("mutex_lock(&selinux_state.policy_mutex);") == 1
            and rules.count("mutex_unlock(&selinux_state.policy_mutex);") == 1,
            "one shared mutex exit")
    require("sidtab_destroy" not in rules and "kfree(old_pol->sidtab)" not in rules,
            "live sidtab is shared with the published clone")
    require("rcu_assign_pointer(selinux_state.policy, backup_sepolicy)" not in rules,
            "hide backup must not masquerade as rollback")

    runtime = src["kernel/runtime/ksud_integration.c"]
    require(runtime.count("#include <linux/atomic.h>") == 1, "atomic include")
    require(runtime.count("static atomic_t ksu_second_stage_attempted = ATOMIC_INIT(0);") == 1,
            "one shared second-stage latch")
    susfs_start = runtime.index("int ksu_handle_execveat_ksud(int *fd,")
    plain_start = runtime.index("void ksu_handle_execveat_ksud(const char *path,")
    sections = ((runtime[susfs_start:plain_start], "return 0;"),
                (body(runtime[plain_start:], "void ksu_handle_execveat_ksud("), "return;"))
    for section, reject in sections:
        ordered(section, 'if (check_argv(*argv, 1, "second_stage", buf, sizeof(buf))) {',
                "if (atomic_cmpxchg(&ksu_second_stage_attempted, 0, 1) != 0) {",
                "refusing replay", reject, 'pr_info("/system/bin/init second_stage executed',
                "ksu_selinux_hide_handle_second_stage();", "if (apply_kernelsu_rules()) {",
                reject, "cache_sid();", "if (setup_ksu_cred()) {", reject,
                "static_branch_disable(&is_init_second_stage_not_executed);")
        require(section.count("atomic_cmpxchg(&ksu_second_stage_attempted, 0, 1)") == 1,
                "one atomic admission per CONFIG alternative")
        require(section.count("ksu_selinux_hide_handle_second_stage();") == 1
                and "ksu_selinux_hide_handle_second_stage();" not in section.split(
                    "if (atomic_cmpxchg(&ksu_second_stage_attempted, 0, 1) != 0) {", 1)[0],
                "hide side effects must wait for atomic admission")
        require(re.search(r"if \(atomic_cmpxchg\(&ksu_second_stage_attempted, 0, 1\) != 0\) \{"
                          r"\s*pr_warn\([^\n]+\);\s*" + re.escape(reject) + r"\s*\}", section),
                "rejected stage must return using its CONFIG return type")
    require(not re.search(r"atomic_set\s*\(\s*&ksu_second_stage_attempted", runtime),
            "no reset after rejection or failure")


def rejected_apply(root, patch):
    result = subprocess.run(["git", "apply", "--check", "--whitespace=error", str(patch)],
                            cwd=root, capture_output=True, timeout=30)
    require(result.returncode != 0, "unexpected duplicate/prerequisite bypass")


def main():
    require(len(sys.argv) == 2, "usage: test_rothko_ksun_g2_snapshot_replay.py PINNED_KSUN")
    upstream = Path(sys.argv[1]).resolve()
    require(git(upstream, "rev-parse", "HEAD").decode().strip() == PIN, "pin mismatch")
    repo = Path(__file__).resolve().parents[1]
    patches = [(name, (repo / "patches" / ("rothko-ksun-" + name + "-candidate.patch"))
                .read_bytes().replace(b"\r\n", b"\n")) for name in NAMES]
    paths = set()
    for _, data in patches:
        paths.update(re.findall(r"^--- a/(.*)$", data.decode(), re.M))
    require(set(re.findall(r"^--- a/(.*)$", patches[-1][1].decode(), re.M)) == CHANGED,
            "new candidate must stay scoped to the two G2 files")
    originals = {p: git(upstream, "show", PIN + ":" + p) for p in paths}
    with tempfile.TemporaryDirectory(prefix="rothko-g2-snapshot-") as td:
        root = Path(td)
        git(root, "init", "-q")
        git(root, "config", "core.autocrlf", "false")
        for p, data in originals.items():
            dst = root / p
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(data)
        new_patch = root / (NAME + ".patch")
        new_patch.write_bytes(patches[-1][1])
        rejected_apply(root, new_patch)
        applied = []
        base_bytes = None
        for i, (name, data) in enumerate(patches):
            if i == len(BASE_NAMES):
                base_bytes = {p: (root / p).read_bytes() for p in paths}
            patch = root / (name + ".patch")
            patch.write_bytes(data)
            flags = ["--unidiff-zero"] if i == 0 else []
            git(root, "apply", "--check", "--whitespace=error", *flags, str(patch))
            git(root, "apply", "--whitespace=error", *flags, str(patch))
            applied.append((patch, flags))
        require(all((root / p).read_bytes() == data for p, data in base_bytes.items()
                    if p not in CHANGED), "existing non-G2 composition changed")
        src = {p: (root / p).read_text(encoding="utf-8") for p in CHANGED}
        contract(src)
        print("PASS: strict 21-stage applicability; focused G2 contract; 11 non-G2 files preserved")
        mutations = (
            ("snapshot before mutex", "kernel/selinux/rules.c", "struct policydb *db;",
             "struct policydb *db;\n    old_pol = selinux_state.policy;"),
            ("policy replay admitted", "kernel/selinux/rules.c", "if (policy_attempted)", "if (false)"),
            ("policy repeat reported success", "kernel/selinux/rules.c", "ret = -EALREADY;", "ret = 0;"),
            ("failed attempt can reset", "kernel/selinux/rules.c", "out_unlock:",
             "out_unlock:\n    policy_attempted = false;"),
            ("null snapshot dereferenced", "kernel/selinux/rules.c", "if (!old_pol)", "if (false)"),
            ("missing policy reported success", "kernel/selinux/rules.c", "ret = -EAGAIN;", "ret = 0;"),
            ("old policy freed before readers drain", "kernel/selinux/rules.c",
             "synchronize_rcu();\n    ksu_destroy_sepolicy(old_pol);",
             "ksu_destroy_sepolicy(old_pol);\n    synchronize_rcu();"),
            ("live sidtab freed", "kernel/selinux/rules.c", "ksu_destroy_sepolicy(old_pol);",
             "sidtab_destroy(old_pol->sidtab);\n    ksu_destroy_sepolicy(old_pol);"),
            ("hide backup treated as rollback", "kernel/selinux/rules.c",
             "rcu_assign_pointer(selinux_state.policy, pol);",
             "rcu_assign_pointer(selinux_state.policy, backup_sepolicy);"),
            ("SUSFS second-stage admission bypassed", "kernel/runtime/ksud_integration.c",
             "if (atomic_cmpxchg(&ksu_second_stage_attempted, 0, 1) != 0)", "if (false)"),
            ("hide side effects before admission", "kernel/runtime/ksud_integration.c",
             "if (atomic_cmpxchg(&ksu_second_stage_attempted, 0, 1) != 0)",
             "ksu_selinux_hide_handle_second_stage();\n                if (atomic_cmpxchg(&ksu_second_stage_attempted, 0, 1) != 0)"),
            ("second-stage latch reset", "kernel/runtime/ksud_integration.c", "refusing replay\\n\");",
             "refusing replay\\n\");\n                    atomic_set(&ksu_second_stage_attempted, 0);"),
        )
        for label, path, old, new in mutations:
            require(old in src[path], "missing mutation target: " + label)
            edited = dict(src)
            edited[path] = src[path].replace(old, new, 1)
            try:
                contract(edited)
            except (RuntimeError, AssertionError, ValueError):
                print("PASS reject:", label)
            else:
                raise RuntimeError("mutation accepted: " + label)
        # The CONFIG alternatives use different return types; exercise the second separately.
        edited = dict(src)
        path = "kernel/runtime/ksud_integration.c"
        start = src[path].index("void ksu_handle_execveat_ksud(const char *path,")
        edited[path] = src[path][:start] + src[path][start:].replace(
            "if (atomic_cmpxchg(&ksu_second_stage_attempted, 0, 1) != 0)", "if (false)", 1)
        try:
            contract(edited)
        except (RuntimeError, AssertionError, ValueError):
            print("PASS reject: non-SUSFS second-stage admission bypassed")
        else:
            raise RuntimeError("non-SUSFS admission mutation accepted")
        rejected_apply(root, new_patch)
        for patch, flags in reversed(applied):
            git(root, "apply", "--reverse", "--check", "--whitespace=error", *flags, str(patch))
            git(root, "apply", "--reverse", "--whitespace=error", *flags, str(patch))
        require(all((root / p).read_bytes() == data for p, data in originals.items()),
                "reverse byte mismatch")
        print("PASS: 13 negative mutations; prerequisite/duplicate rejection; 13 files restored exactly")
    print("SOURCE-ONLY PASS; rollback, rule errors, hide readers and startup transaction remain BLOCKED")


if __name__ == "__main__":
    main()
