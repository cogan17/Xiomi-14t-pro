#!/usr/bin/env python3
"""Focused source/patch contract for preparation errors and escape callers."""
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from test_rothko_ksun_app_profile_precommit import NAMES as BASE_NAMES
from test_rothko_ksun_g5_composition import PIN, body, contract as g5_contract, git, ordered, require

NAMES = BASE_NAMES + ("app-profile-precommit-composable", "su-escape-caller-status")


def inline_body(text, signature):
    start = text.index(signature)
    return text[start:text.index("\n}", start) + 2]


def contract(src):
    g5_contract(src)
    app = src["policy/app_profile.c"]
    groups = body(app, "static int setup_groups(")
    ordered(groups, "if (profile->groups_count > KSU_MAX_GROUPS)", "return -EINVAL;",
            "groups_alloc(ngroups)", "if (!group_info)", "return -ENOMEM;",
            "if (!gid_valid(kgid))", "put_group_info(group_info);", "return -EINVAL;",
            "groups_sort(group_info);", "set_groups(cred, group_info);", "return 0;")
    root = body(app, "int escape_with_root_profile(void)")
    ordered(root, "Already root, don't escape!", "ret = -EALREADY;", "goto out_abort_creds;",
            "TIF_KSU_DISABLE_ESCAPE_WITH_ROOT found", "ret = -EPERM;", "goto out_abort_creds;",
            "ksu_mount_ns_precommit_status(profile->namespaces)", "cred->uid.val = profile->uid;")
    ordered(root, "ret = set_cred_ucounts(cred);", "if (ret)", "goto out_abort_creds;",
            "ret = setup_groups(profile, cred);", "if (ret)", "goto out_abort_creds;",
            "ret = setup_selinux(profile->selinux_domain, cred);", "if (ret)", "goto out_abort_creds;",
            "seccomp_scratch = kmalloc", "if (!seccomp_scratch)", "ret = -ENOMEM;",
            "goto out_abort_creds;", "commit_creds(cred);", "disable_seccomp_with_scratch(seccomp_scratch);")
    require(root.count("commit_creds(cred);") == 1, "one checked profile commit")
    require(root.count("kfree(seccomp_scratch);") == 2, "success/abort scratch cleanup")
    require("kmalloc" not in root.split("commit_creds(cred);", 1)[1], "no scratch allocation after commit")
    ordered(root, "out_abort_creds:", "if (profile)", "ksu_put_root_profile(profile);",
            "abort_creds(cred);", "kfree(seccomp_scratch);", "return ret;")
    helper = body(app, "static void disable_seccomp_with_scratch(")
    require(not re.search(r"\b(?:kmalloc|kfree)\s*\(", helper), "helper must not allocate/free scratch")
    ordered(helper, "spin_lock_irq(&current->sighand->siglock);", "memcpy(fake, current, sizeof(*fake));",
            "spin_unlock_irq(&current->sighand->siglock);", "seccomp_filter_release(fake);")
    require("void disable_seccomp(void)" in app, "public setuid wrapper preserved")
    init = body(app, "int escape_to_root_for_init(void)")
    ordered(init, "ret = setup_selinux(KERNEL_SU_CONTEXT, cred);", "if (ret) {",
            "abort_creds(cred);", "return ret;", "commit_creds(cred);")
    require("setup_mount_ns(" not in app, "no postcommit namespace reintroduced")

    su = src["feature/sucompat.c"]
    init_hook = inline_body(su, "int ksu_handle_execveat_init(")
    require("is_init(current_cred())" in init_hook and "get_current_cred()" not in init_hook,
            "init predicate must not leak a cred reference")
    ordered(init_hook, "if (!argv_user_ptr || IS_ERR(argv_user_ptr))", "return -EFAULT;",
            "ret = escape_to_root_for_init();", "if (ret) {", "return ret;")
    require(init_hook.rstrip().endswith("return 1; /* Not an init request: continue ordinary su checks. */\n}"),
            "ordinary exec must use positive not-init sentinel")
    filename = inline_body(su, "int ksu_handle_execveat_sucompat(int *fd,")
    ordered(filename, "ret = ksu_handle_execveat_init(", "if (ret <= 0)", "return ret;",
            "replacement = getname_kernel(ksud_path);", "if (IS_ERR(replacement))",
            "ret = PTR_ERR(replacement);", "ksu_sulog_emit_pending(pending_sucompat, ret, GFP_KERNEL);",
            "return ret;", "ret = escape_with_root_profile();", "if (ret) {", "putname(replacement);",
            "ksu_sulog_emit_pending(pending_sucompat, ret, GFP_KERNEL);", "return ret;",
            "*filename_ptr = replacement;", "putname(filename);")
    require("memcpy((void *)filename->name" not in filename, "no mutation of old filename")
    require("GLOBAL_ROOT_UID" not in filename and "susfs_is_current_ksu_domain()" not in filename,
            "selected custom profiles must not be forced to default UID/domain")
    before_escape = filename.split("ret = escape_with_root_profile();", 1)[0]
    require("*filename_ptr =" not in before_escape, "filename publication must wait for escape")
    fd = body(su, "static long ksu_handle_execve_sucompat_common(")
    ordered(fd, "fd_install(tmp_fd, ksud_file);", "empty_path = empty_user_path();",
            "if (!empty_path) {", "ret = -EFAULT;",
            "ksu_sulog_emit_pending(pending_sucompat, ret, GFP_KERNEL);", "ksu_close_fd(tmp_fd);", "return ret;",
            "ret = escape_with_root_profile();", "if (ret) {",
            "ksu_sulog_emit_pending(pending_sucompat, ret, GFP_KERNEL);", "ksu_close_fd(tmp_fd);", "return ret;",
            "orig_regs[0] =", "regs->__PT_PARM5_REG = AT_EMPTY_PATH;",
            "ksu_syscall_table[__NR_execveat](regs)")
    require(not re.search(r"regs->__PT_\w+\s*=", fd.split("ret = escape_with_root_profile();", 1)[0]),
            "no register mutation before escape")
    require(fd.count("ksu_return_cred(borrowed);") == 1, "borrow returned exactly once before FD install")
    after_install = fd.split("fd_install(tmp_fd, ksud_file);", 1)[1]
    require("put_unused_fd" not in after_install and "fput(" not in after_install,
            "installed fd must close through fd table")
    for i, field in enumerate(("__PT_PARM1_REG", "__PT_PARM2_REG", "__PT_PARM3_REG",
                               "__PT_SYSCALL_PARM4_REG", "__PT_PARM5_REG")):
        require(f"regs->{field} = orig_regs[{i}];" in fd, "postexec error register restore")
    bridge = src["hook/syscall_event_bridge.c"]
    tracker = body(bridge, "static int ksu_handle_init_mark_tracker(")
    require("return escape_to_root_for_init();" in tracker, "tracker must propagate status")
    hook = body(bridge, "static long __nocfi ksu_hook_execve_common(")
    ordered(hook, "ret = ksu_handle_init_mark_tracker(filename_user);", "if (ret) {",
            "ksu_sulog_emit_pending(pending_root_execve, ret, GFP_KERNEL);", "return ret;",
            "ksu_adb_root_handle_execveat", "if (ret) {",
            "ksu_sulog_emit_pending(pending_root_execve, ret, GFP_KERNEL);", "return ret;",
            "ret = ksu_syscall_table[orig_nr](regs);")


def main():
    require(len(sys.argv) == 2, "usage: test_rothko_ksun_escape_precommit.py PINNED_KSUN")
    upstream = Path(sys.argv[1]).resolve()
    require(git(upstream, "rev-parse", "HEAD").decode().strip() == PIN, "pin mismatch")
    repo = Path(__file__).resolve().parents[1]
    patches = [(n, (repo / "patches" / ("rothko-ksun-" + n + "-candidate.patch"))
                .read_bytes().replace(b"\r\n", b"\n")) for n in NAMES]
    paths = set()
    for _, data in patches:
        paths.update(re.findall(r"^--- a/(.*)$", data.decode(), re.M))
    originals = {p: git(upstream, "show", PIN + ":" + p) for p in paths}
    with tempfile.TemporaryDirectory(prefix="rothko-escape-precommit-") as td:
        root = Path(td)
        git(root, "init", "-q")
        git(root, "config", "core.autocrlf", "false")
        for p, data in originals.items():
            dst = root / p
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
        src = {p.removeprefix("kernel/"): (root / p).read_text(encoding="utf-8") for p in paths}
        contract(src)
        print("PASS: strict 20-stage composition and preparation/caller source contracts")
        mutations = (
            ("group allocation error lost", "policy/app_profile.c", "return -ENOMEM;", "return 0;"),
            ("group gid cleanup lost", "policy/app_profile.c", "put_group_info(group_info);\n            return -EINVAL;", "return -EINVAL;"),
            ("ucounts status ignored", "policy/app_profile.c", "ret = set_cred_ucounts(cred);", "set_cred_ucounts(cred);"),
            ("groups status ignored", "policy/app_profile.c", "ret = setup_groups(profile, cred);", "setup_groups(profile, cred);"),
            ("already root reported success", "policy/app_profile.c", "ret = -EALREADY;", "ret = 0;"),
            ("disabled escape reported success", "policy/app_profile.c", "ret = -EPERM;", "ret = 0;"),
            ("scratch allocation error bypassed", "policy/app_profile.c", "if (!seccomp_scratch)", "if (false)"),
            ("scratch abort cleanup removed", "policy/app_profile.c", "abort_creds(cred);\n    kfree(seccomp_scratch);", "abort_creds(cred);"),
            ("helper allocates after commit", "policy/app_profile.c", "static void disable_seccomp_with_scratch(struct task_struct *fake)\n{", "static void disable_seccomp_with_scratch(struct task_struct *fake)\n{\n    fake = kmalloc(sizeof(*fake), GFP_KERNEL);"),
            ("init predicate leaks cred", "feature/sucompat.c", "is_init(current_cred())", "is_init(get_current_cred())"),
            ("ordinary exec treated as failure", "feature/sucompat.c", "return 1; /* Not an init request: continue ordinary su checks. */", "return -EINVAL;"),
            ("init error ignored", "feature/sucompat.c", "if (ret <= 0)", "if (ret == 0)"),
            ("filename failure release removed", "feature/sucompat.c", "putname(replacement);", ""),
            ("filename published before escape", "feature/sucompat.c", "replacement = getname_kernel(ksud_path);", "replacement = getname_kernel(ksud_path);\n    *filename_ptr = replacement;"),
            ("FD escape guard bypassed", "feature/sucompat.c", "if (ret) {\n\t\tpr_err(\"escape_with_root_profile failed:", "if (false) {\n\t\tpr_err(\"escape_with_root_profile failed:"),
            ("FD failure cleanup removed", "feature/sucompat.c", "ksu_close_fd(tmp_fd);\n\t\treturn ret;", "return ret;"),
            ("register modified before escape", "feature/sucompat.c", "empty_path = empty_user_path();", "empty_path = empty_user_path();\n\tregs->__PT_PARM5_REG = AT_EMPTY_PATH;"),
            ("init tracker drops error", "hook/syscall_event_bridge.c", "return escape_to_root_for_init();", "escape_to_root_for_init();"),
            ("bridge failure pending leaked", "hook/syscall_event_bridge.c", "ksu_sulog_emit_pending(pending_root_execve, ret, GFP_KERNEL);", ""),
            ("bridge error becomes success", "hook/syscall_event_bridge.c", "return ret;", "return 0;"),
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
        for patch, _ in applied[-2:]:
            result = subprocess.run(["git", "apply", "--check", "--whitespace=error", str(patch)],
                                    cwd=root, capture_output=True, timeout=30)
            require(result.returncode != 0, "duplicate new candidate accepted")
        for patch, flags in reversed(applied):
            git(root, "apply", "--reverse", "--check", "--whitespace=error", *flags, str(patch))
            git(root, "apply", "--reverse", "--whitespace=error", *flags, str(patch))
        require(all((root / p).read_bytes() == data for p, data in originals.items()), "reverse byte mismatch")
        print("PASS: duplicate rejection; exact reverse restoration for", len(paths), "source files")
    print("SOURCE-ONLY PASS; ADB transaction, late-load unwind, BSP hook propagation and runtime remain BLOCKED")


if __name__ == "__main__":
    main()
