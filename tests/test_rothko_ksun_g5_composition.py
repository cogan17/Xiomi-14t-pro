#!/usr/bin/env python3
"""Strict isolated KSUN candidate composition. No build or runtime proof."""
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from test_rothko_ksun_g5_setup_serialization import contract as setup_contract

PIN = "3438d6aa431f96a23f9e625bec3d53ce1fb14161"
NAMES = (
    "g1-selinux-return-contract", "shared-cred-status", "g5-cred-borrow-api",
    "g5-ready-repeat-setup-guard", "g5-selinux-ready-publication",
    "g5-initial-setup-serialization", "shared-cred-stage-guard",
    "g5-kernel-umount-borrow", "g5-allowlist-borrow",
    "g5-sucompat-borrow-composable", "g5-module-rc-composable",
    "g5-mount-ns-borrow", "g2-policy-backup-preflight", "g2-policy-error-status",
    "g2-second-stage-status-guard", "lateload-g2-cred-escape-gate",
)
CONSUMERS = ("feature/kernel_umount.c", "policy/allowlist.c", "feature/sucompat.c",
             "runtime/ksud_integration.c", "infra/su_mount_ns.c")


def require(value, message):
    if not value:
        raise RuntimeError(message)


def git(root, *args):
    result = subprocess.run(["git", "-c", "safe.directory=" + str(root), *args],
                            cwd=root, capture_output=True, timeout=30)
    require(result.returncode == 0, result.stderr.decode(errors="replace"))
    return result.stdout


def body(text, signature):
    start = text.index(signature)
    opening = text.index("\n{", start)
    return text[start:text.index("\n}", opening) + 2]


def ordered(text, *tokens):
    pos = 0
    for token in tokens:
        pos = text.index(token, pos) + len(token)


def contract(src):
    core, runtime = src["core/init.c"], src["runtime/ksud_integration.c"]
    setup_contract(core, src["selinux/selinux.c"], src["selinux/selinux.h"])
    for name in CONSUMERS:
        require(not re.search(r"\bksu_cred\b", src[name]), "raw owner access: " + name)
    require(sum(s.count("override_creds(borrowed)") for s in src.values()) == 7,
            "all seven overrides must use a borrowed reference")
    require("dentry_open(&ns_path, O_RDONLY, borrowed)" in src["infra/su_mount_ns.c"],
            "namespace open must share the same reference")
    loader = body(runtime, "static bool load_module_rc_once(void)")
    lock_at = loader.index("mutex_lock(&load_lock);")
    require("if (loaded)" not in loader[:lock_at], "unlocked loaded fast path")
    ordered(loader, "bool accepted = false;", "mutex_lock(&load_lock);",
            "borrowed = ksu_borrow_ready_cred();", "if (!borrowed)",
            "goto out_unlock;", "if (loaded)", "goto out_return_cred;")
    ordered(loader, "loaded = true;", "old_cred = override_creds(borrowed);",
            "out_revert_creds:", "revert_creds(old_cred);", "out_return_cred:",
            "ksu_return_cred(borrowed);", "accepted = true;", "out_unlock:",
            "mutex_unlock(&load_lock);", "return accepted;")
    hook = body(runtime, "static void ksu_install_rc_hook(struct file *file)")
    ordered(hook, "mutex_lock(&rc_hook_lock);", "if (rc_hooked)",
            "if (!load_module_rc_once())", "goto out_unlock;", "rc_hooked = true;",
            "static_branch_disable", "stop_init_rc_hook();", "file->f_op = &fops_proxy;",
            "out_unlock:", "mutex_unlock(&rc_hook_lock);")
    require(runtime.count("if (setup_ksu_cred()) {") == 3, "three boot status guards")
    require(runtime.count("if (apply_kernelsu_rules()) {") == 2, "two policy status guards")
    init = body(core, "int __init kernelsu_init(void)")
    ordered(init, "rules_ret = apply_kernelsu_rules();", "if (!rules_ret)",
            "cred_ret = setup_ksu_cred();", "if (!rules_ret && !cred_ret)",
            "escape_to_root_for_init();")
    allow = body(src["policy/allowlist.c"], "static void do_persistent_allow_list(struct callback_head *_cb)")
    ordered(allow, "if (!borrowed)", "goto free_callback;", "override_creds(borrowed)",
            "revert_creds(saved);", "ksu_return_cred(borrowed);", "free_callback:", "kfree(_cb);")
    ns = body(src["infra/su_mount_ns.c"], "void setup_mount_ns(int32_t ns_mode)")
    ordered(ns, "borrowed = ksu_borrow_ready_cred();", "if (!borrowed)", "return;",
            "override_creds(borrowed)", "ksu_mnt_ns_global(borrowed);",
            "revert_creds(old_cred);", "ksu_return_cred(borrowed);")
    su = src["feature/sucompat.c"]
    require(su.count("ksu_return_cred(borrowed);") == 5, "all sucompat return branches")
    exec_su = body(su, "static long ksu_handle_execve_sucompat_common(")
    ordered(exec_su, "if (!borrowed) {", "put_unused_fd(tmp_fd);", "goto do_orig_execve;",
            "old_cred = override_creds(borrowed);", "filp_open(KSUD_PATH",
            "revert_creds(old_cred);", "ksu_return_cred(borrowed);")


def main():
    require(len(sys.argv) == 2, "usage: test_rothko_ksun_g5_composition.py PINNED_KSUN")
    upstream = Path(sys.argv[1]).resolve()
    require(git(upstream, "rev-parse", "HEAD").decode().strip() == PIN, "pin mismatch")
    repo = Path(__file__).resolve().parents[1]
    patches = [(n, (repo / "patches" / ("rothko-ksun-" + n + "-candidate.patch"))
                .read_bytes().replace(b"\r\n", b"\n")) for n in NAMES]
    paths = set()
    for _, data in patches:
        paths.update(re.findall(r"^--- a/(.*)$", data.decode(), re.M))
    originals = {p: git(upstream, "show", PIN + ":" + p) for p in paths}
    with tempfile.TemporaryDirectory(prefix="rothko-g5-composition-") as td:
        root = Path(td)
        git(root, "init", "-q")
        git(root, "config", "core.autocrlf", "false")
        for name, data in originals.items():
            dst = root / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(data)
        applied = []
        for i, (name, data) in enumerate(patches):
            patch = root / (name + ".patch")
            patch.write_bytes(data)
            flags = ["--unidiff-zero"] if i == 0 else []
            git(root, "apply", "--check", "--whitespace=error", *flags, str(patch))
            git(root, "apply", "--whitespace=error", *flags, str(patch))
            applied.append((patch, flags))
            print("PASS compose:", name)
        src = {p.removeprefix("kernel/"): (root / p).read_text(encoding="utf-8") for p in paths}
        contract(src)
        mutations = (
            ("raw namespace override", "infra/su_mount_ns.c", "override_creds(borrowed)", "override_creds(ksu_cred)"),
            ("raw namespace open", "infra/su_mount_ns.c", "O_RDONLY, borrowed)", "O_RDONLY, ksu_cred)"),
            ("namespace release removed", "infra/su_mount_ns.c", "ksu_return_cred(borrowed);", ""),
            ("allowlist release removed", "policy/allowlist.c", "ksu_return_cred(borrowed);", ""),
            ("sucompat branch release removed", "feature/sucompat.c", "ksu_return_cred(borrowed);", ""),
            ("exec fd release removed", "feature/sucompat.c", "if (!borrowed) {\n\t\tput_unused_fd(tmp_fd);", "if (!borrowed) {"),
            ("loader mutex removed", "runtime/ksud_integration.c", "mutex_lock(&load_lock);", ""),
            ("unlocked loaded fast path", "runtime/ksud_integration.c", "mutex_lock(&load_lock);", "if (loaded) return true;\n    mutex_lock(&load_lock);"),
            ("loader borrow failure bypassed", "runtime/ksud_integration.c", "if (!borrowed)", "if (false)"),
            ("rc consumes unavailable READY", "runtime/ksud_integration.c", "if (!load_module_rc_once())", "if (false)"),
            ("rc latch mutex removed", "runtime/ksud_integration.c", "mutex_lock(&rc_hook_lock);", ""),
            ("boot status ignored", "runtime/ksud_integration.c", "if (setup_ksu_cred()) {", "if (false) {"),
            ("late-load gate bypassed", "core/init.c", "if (!rules_ret && !cred_ret)", "if (true)"),
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
        for patch, flags in reversed(applied):
            git(root, "apply", "--reverse", "--check", "--whitespace=error", *flags, str(patch))
            git(root, "apply", "--reverse", "--whitespace=error", *flags, str(patch))
        require(all((root / p).read_bytes() == data for p, data in originals.items()), "reverse byte mismatch")
        print("PASS reverse: exact pinned bytes restored for", len(paths), "source files")
    print("SOURCE-ONLY composition PASS; kernel integration/runtime/release remain BLOCKED")


if __name__ == "__main__":
    main()
