#!/usr/bin/env python3
"""Read-only source-contract audit of a *pinned, already patched* KSUN checkout.

A PASS means that the expected SOURCE EVIDENCE was found. It is NOT a kernel
compile, credential/FD authorization proof, or approval to merge or flash.
Network access is not used. This script never modifies upstream files.
"""
from pathlib import Path
import sys


def source(root: Path, name: str) -> str:
    target = root / name
    if not target.is_file():
        raise FileNotFoundError(f"required KSUN source absent: {name}")
    return target.read_text(encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: rothko_ksun_security_contract.py /path/to/pinned-ksun/kernel", file=sys.stderr)
        return 2
    root = Path(sys.argv[1])
    su = source(root, "feature/sucompat.c")
    policy = source(root, "policy/app_profile.c")
    perm = source(root, "supercall/perm.c")
    dispatch = source(root, "supercall/dispatch.c")
    supercall = source(root, "supercall/supercall.c")
    selinux = source(root, "selinux/selinux.c")
    selinux_h = source(root, "selinux/selinux.h")
    bridge = source(root, "hook/syscall_event_bridge.c")
    results: list[tuple[str, bool]] = []

    def check(label: str, condition: bool) -> None:
        results.append((label, condition))
        print(("PASS" if condition else "REVIEW REQUIRED") + ": " + label, flush=True)

    grant_entry = dispatch.split(".cmd = KSU_IOCTL_GRANT_ROOT", 1)
    grant_block = grant_entry[1].split("}", 1)[0] if len(grant_entry) == 2 else ""
    ioctl_handler = dispatch.split("long ksu_supercall_handle_ioctl(", 1)
    ioctl_block = ioctl_handler[1].split("void __init ksu_supercall_dump_commands(", 1)[0] if len(ioctl_handler) == 2 else ""
    escape = policy.split("int escape_with_root_profile(void)", 1)
    escape_body = escape[1].split("int escape_to_root_for_init(void)", 1)[0] if len(escape) == 2 else ""
    before_commit = escape_body.split("commit_creds(cred);", 1)[0]
    init_escape = policy.split("int escape_to_root_for_init(void)", 1)
    init_body = init_escape[1].split("void __init ksu_app_profile_init(void)", 1)[0] if len(init_escape) == 2 else ""
    cred_init = selinux.split("void setup_ksu_cred(void)", 1)
    cred_init_body = cred_init[1].split("void escape_to_root_for_adb_root(void)", 1)[0] if len(cred_init) == 2 else ""
    fd_install = supercall.split("int ksu_install_fd(void)", 1)
    fd_body = fd_install[1].split("static void ksu_install_fd_tw_func(", 1)[0] if len(fd_install) == 2 else ""

    # These are concrete upstream ENTRY-POINT checks, not a general
    # authorization theorem for every caller of escape_with_root_profile.
    check("sucompat checks chroot and current UID allowlist",
          "current_chrooted()" in su and
          "if (!ksu_is_allow_uid_for_current(current_uid().val))" in su)
    check("GRANT_ROOT ioctl maps to allowed_for_su",
          ".perm_check = allowed_for_su" in grant_block and
          "return is_manager() || ksu_is_allow_uid_for_current(current_uid().val);" in perm)
    check("ioctl dispatch rechecks permission on each command",
          "ksu_ioctl_handlers[i].perm_check()" in ioctl_block and
          "return -EPERM;" in ioctl_block)
    check("candidate redirects su filename only after checking escape",
          "replacement = getname_kernel(ksud_path)" in su and
          "ret = escape_with_root_profile();" in su and
          "if (!uid_eq(current_euid(), GLOBAL_ROOT_UID)" in su and
          "*filename_ptr = replacement;" in su)
    check("candidate propagates group and SELinux errors before commit",
          "ret = setup_groups(profile, cred);" in before_commit and
          "ret = setup_selinux(profile->selinux_domain, cred);" in before_commit and
          "goto out_abort_creds;" in before_commit)
    check("candidate aborts init escalation when SELinux setup fails",
          "if (setup_selinux(KERNEL_SU_CONTEXT, cred)) {" in init_body and
          "abort_creds(cred);" in init_body)
    check("SELinux helper reports status in candidate",
          "int setup_selinux(const char *, struct cred *);" in selinux_h and
          "int setup_selinux(const char *domain, struct cred *cred)" in selinux)
    check("candidate preallocates seccomp scratch before credential commit",
          "seccomp_scratch = kmalloc(" in before_commit and
          "if (!seccomp_scratch)" in before_commit and
          "disable_seccomp_with_scratch(seccomp_scratch);" in escape_body)
    check("existing KSUN FD installer uses close-on-exec",
          "get_unused_fd_flags(O_CLOEXEC)" in fd_body and
          "anon_inode_getfile(" in fd_body)
    check("SUSFS reboot path queues task_work to install FD",
          "int ksu_supercall_reboot_handler(" in supercall and
          "task_work_add(current, &tw->cb, TWA_RESUME)" in supercall)
    check("FD ioctl passes to command-specific permission checks",
          "return ksu_supercall_handle_ioctl(cmd, (void __user *)arg);" in supercall and
          "ksu_ioctl_handlers[i].perm_check()" in ioctl_block)
    # An absent symbol here is an EXPECTED RELEASE BLOCKER, not a feature pass.
    check("post-exec SUSFS companion handler still absent from inspected KSUN paths",
          "ksu_handle_post_execveat_sucompat" not in su and
          "ksu_handle_post_execveat_sucompat" not in bridge)
    check("setup_ksu_cred still logs SELinux failure without propagating it",
          "void setup_ksu_cred(void)" in selinux and
          "if (setup_selinux(KERNEL_SU_CONTEXT, ksu_cred))" in cred_init_body and
          "pr_err(" in cred_init_body)

    print("\nRELEASE GATE: BLOCKED — the checks above only establish source structure.")
    print("BLOCK: no verified pre-commit grant proof across every escalation entry.")
    print("BLOCK: setup_ksu_cred error ownership and fail-closed behavior unresolved.")
    print("BLOCK: existing O_CLOEXEC fd is not an authenticated post-exec session contract.")
    print("BLOCK: execve/SUSFS hook ownership, Rothko BSP hunks, ABI/KMI and runtime unverified.")
    if not all(ok for _, ok in results):
        print("AUDIT: FAILED — source changed or expected evidence is missing.", file=sys.stderr)
        return 1
    print("AUDIT: PASS — expected static evidence present; release remains BLOCKED.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeError) as exc:
        print(f"AUDIT: FAILED — {exc}", file=sys.stderr)
        raise SystemExit(1)
