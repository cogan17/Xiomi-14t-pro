#!/usr/bin/env python3
"""Fail-closed source audit for the pinned KSUN ioctl permission table.

Records explicit upstream permission classes. This is NOT a privilege,
SELinux, FD-session, kernel runtime, or release authorization proof.
"""
import re
import sys
from pathlib import Path

# Full command-to-permission snapshot from pinned pershoot/KernelSU-Next:
# 3438d6aa431f96a23f9e625bec3d53ce1fb14161. Every addition/deletion,
# rename, or permission change must be reviewed (even more restrictive ones).
EXPECTED = {
    "KSU_IOCTL_GRANT_ROOT": "allowed_for_su",
    "KSU_IOCTL_GET_INFO": "always_allow",
    "KSU_IOCTL_GET_INFO_LEGACY": "always_allow",
    "KSU_IOCTL_REPORT_EVENT": "only_root",
    "KSU_IOCTL_SET_SEPOLICY": "only_root",
    "KSU_IOCTL_CHECK_SAFEMODE": "always_allow",
    "KSU_IOCTL_GET_ALLOW_LIST": "manager_or_root",
    "KSU_IOCTL_GET_DENY_LIST": "manager_or_root",
    "KSU_IOCTL_NEW_GET_ALLOW_LIST": "manager_or_root",
    "KSU_IOCTL_NEW_GET_DENY_LIST": "manager_or_root",
    "KSU_IOCTL_UID_GRANTED_ROOT": "manager_or_root",
    "KSU_IOCTL_UID_SHOULD_UMOUNT": "manager_or_root",
    "KSU_IOCTL_GET_MANAGER_APPID": "manager_or_root",
    "KSU_IOCTL_GET_APP_PROFILE": "only_manager",
    "KSU_IOCTL_SET_APP_PROFILE": "only_manager",
    "KSU_IOCTL_GET_FEATURE": "manager_or_root",
    "KSU_IOCTL_SET_FEATURE": "manager_or_root",
    "KSU_IOCTL_GET_WRAPPER_FD": "manager_or_root",
    "KSU_IOCTL_MANAGE_MARK": "manager_or_root",
    "KSU_IOCTL_NUKE_EXT4_SYSFS": "manager_or_root",
    "KSU_IOCTL_ADD_TRY_UMOUNT": "manager_or_root",
    "KSU_IOCTL_SET_INIT_PGRP": "only_root",
    "KSU_IOCTL_GET_SULOG_FD": "only_root",
    "KSU_IOCTL_DISABLE_ESCAPE_TO_ROOT": "only_root",
    "KSU_IOCTL_GET_HOOK_MODE": "manager_or_root",
    "KSU_IOCTL_GET_VERSION_TAG": "manager_or_root",
}

REQUIRED_PERM_BODIES = {
    "only_manager": "return is_manager();",
    "only_root": "return current_uid().val == 0;",
    "manager_or_root": "return current_uid().val == 0 || is_manager();",
    "always_allow": "return true;",
    "allowed_for_su": "return is_manager() || ksu_is_allow_uid_for_current(current_uid().val);",
}


def fail(reason):
    print("AUDIT: FAILED — " + reason, file=sys.stderr)
    raise SystemExit(1)


def get_function(text, signature):
    marker = re.search(r"\b" + re.escape(signature) + r"\s*\{", text)
    if not marker:
        fail(f"missing function: {signature}")
    start = marker.end()
    depth = 1
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start:i]
    fail("unbalanced braces in " + signature)


def main():
    if len(sys.argv) != 2:
        print("usage: rothko_ksun_ioctl_matrix.py /path/to/pinned-ksun/kernel", file=sys.stderr)
        return 2
    root = Path(sys.argv[1])
    try:
        dispatch = (root / "supercall/dispatch.c").read_text(encoding="utf-8")
        perm = (root / "supercall/perm.c").read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        fail(f"missing or unreadable pinned source: {exc}")

    start = "static const struct ksu_ioctl_cmd_map ksu_ioctl_handlers[] = {"
    end = "// clang-format on"
    if dispatch.count(start) != 1 or dispatch.count(end) != 1:
        fail("missing or duplicated ioctl command table markers")
    table = dispatch.split(start, 1)[1].split(end, 1)[0]
    actual = {}
    for match in re.finditer(r"\{([^{}]*)\}", table):
        chunk = match.group(1)
        command = re.search(r"\.cmd\s*=\s*(KSU_IOCTL_[A-Z0-9_]+|0)\s*,", chunk)
        if not command:
            fail("unparseable ioctl command table entry")
        cmd = command.group(1)
        if cmd == "0":
            if not re.search(r"\.handler\s*=\s*NULL", chunk):
                fail("unexpected nonempty table sentinel")
            continue
        name = re.search(r"\.name\s*=\s*\"([^\"]+)\"\s*,", chunk)
        handler = re.search(r"\.handler\s*=\s*([a-zA-Z_]\w*)\s*,", chunk)
        check = re.search(r"\.perm_check\s*=\s*([a-zA-Z_]\w*)\s*,?\s*$", chunk)
        if not (name and handler and check):
            fail(f"incomplete ioctl table entry: {cmd}")
        if cmd in actual:
            fail(f"duplicate command: {cmd}")
        actual[cmd] = check.group(1)
    missing = sorted(set(EXPECTED) - set(actual))
    unknown = sorted(set(actual) - set(EXPECTED))
    changed = [cmd for cmd in EXPECTED if cmd in actual and actual[cmd] != EXPECTED[cmd]]
    if missing or unknown or changed:
        fail(f"table drift: missing={missing}, new={unknown}, permission_changes=" +
             str([(cmd, EXPECTED[cmd], actual[cmd]) for cmd in changed]))

    for label, expected_return in REQUIRED_PERM_BODIES.items():
        body = get_function(perm, f"bool {label}(void)")
        statement = re.sub(r"\s+", "", body)
        if statement != re.sub(r"\s+", "", expected_return):
            fail(f"permission helper changed: {label}")

    body = get_function(dispatch, "long ksu_supercall_handle_ioctl(unsigned int cmd, void __user *argp)")
    guard = "ksu_ioctl_handlers[i].perm_check && !ksu_ioctl_handlers[i].perm_check()"
    denial = "return -EPERM;"
    invocation = "return ksu_ioctl_handlers[i].handler(argp);"
    if guard not in body or denial not in body or invocation not in body:
        fail("missing per-command permission guard, denial, or dispatch")
    if not (body.index(guard) < body.index(denial) < body.index(invocation)):
        fail("ioctl permission check no longer precedes command dispatch")

    for perm_class in ("only_root", "only_manager", "manager_or_root", "allowed_for_su", "always_allow"):
        count = sum(x == perm_class for x in actual.values())
        print(f"PASS: {perm_class}: {count} commands (source snapshot)", flush=True)
    print("PASS: every pinned ioctl permission class and helper matched the reviewed snapshot")
    print("BLOCK: only_root currently tests UID 0, not a KSU-domain assertion")
    print("BLOCK: ioctl permissions do not prove FD installation/session authorization")
    print("BLOCK: no kernel build, SELinux hook validation, ABI/KMI or runtime proof")
    print("AUDIT: PASS (source snapshot only); RELEASE GATE: BLOCKED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
