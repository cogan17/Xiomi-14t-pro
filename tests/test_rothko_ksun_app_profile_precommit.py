#!/usr/bin/env python3
"""Source-only app-profile status/admission contract over the G5 composition."""
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from test_rothko_ksun_g5_composition import (
    PIN, NAMES as BASE_NAMES, body, contract as g5_contract, git, ordered, require,
)

NAMES = BASE_NAMES + ("app-profile-selinux-status", "namespace-precommit-admission")


def contract(src):
    g5_contract(src)
    ns = src["infra/su_mount_ns.c"]
    admission = body(ns, "int ksu_mount_ns_precommit_status(int32_t ns_mode)")
    require(re.search(r"case KSU_NS_INHERITED:\s*return 0;", admission), "inherited must be admitted")
    require(re.search(r"case KSU_NS_GLOBAL:\s*case KSU_NS_INDIVIDUAL:\s*return -EOPNOTSUPP;", admission),
            "namespace transactions must be denied")
    require(re.search(r"default:\s*return -EINVAL;", admission), "invalid mode must fail")
    require(not re.search(r"\b(?:ksys_unshare|ksu_sys_setns|path_mount|override_creds|commit_creds)\s*\(", admission),
            "admission may not change current state")
    require("int ksu_mount_ns_precommit_status(int32_t ns_mode);" in src["infra/su_mount_ns.h"],
            "admission declaration missing")
    app = src["policy/app_profile.c"]
    root = body(app, "int escape_with_root_profile(void)")
    ordered(root, "profile = ksu_get_root_profile(cred->uid.val);",
            "ret = ksu_mount_ns_precommit_status(profile->namespaces);",
            "if (ret)", "goto out_abort_creds;", "cred->uid.val = profile->uid;",
            "ret = setup_selinux(profile->selinux_domain, cred);", "if (ret)",
            "goto out_abort_creds;", "commit_creds(cred);", "disable_seccomp();")
    require(root.count("commit_creds(cred);") == 1, "profile commit must occur only on checked path")
    require(not re.search(r"\bsetup_mount_ns\s*\(", app), "no postcommit namespace operation admitted")
    ordered(root, "out_abort_creds:", "if (profile)", "ksu_put_root_profile(profile);",
            "abort_creds(cred);", "return ret;")
    init = body(app, "int escape_to_root_for_init(void)")
    ordered(init, "ret = setup_selinux(KERNEL_SU_CONTEXT, cred);", "if (ret) {",
            "abort_creds(cred);", "return ret;", "commit_creds(cred);", "return 0;")
    require(init.count("commit_creds(cred);") == 1, "init commit must occur only on checked path")


def rejected_apply(root, patch):
    result = subprocess.run(["git", "apply", "--check", "--whitespace=error", str(patch)],
                            cwd=root, capture_output=True, timeout=30)
    require(result.returncode != 0, "duplicate/prerequisite bypass unexpectedly applicable: " + patch.name)


def main():
    require(len(sys.argv) == 2, "usage: test_rothko_ksun_app_profile_precommit.py PINNED_KSUN")
    upstream = Path(sys.argv[1]).resolve()
    require(git(upstream, "rev-parse", "HEAD").decode().strip() == PIN, "pin mismatch")
    repo = Path(__file__).resolve().parents[1]
    patches = [(name, (repo / "patches" / ("rothko-ksun-" + name + "-candidate.patch"))
                .read_bytes().replace(b"\r\n", b"\n")) for name in NAMES]
    paths = set()
    for _, data in patches:
        paths.update(re.findall(r"^--- a/(.*)$", data.decode(), re.M))
    originals = {p: git(upstream, "show", PIN + ":" + p) for p in paths}
    with tempfile.TemporaryDirectory(prefix="rothko-profile-precommit-") as td:
        root = Path(td)
        git(root, "init", "-q")
        git(root, "config", "core.autocrlf", "false")
        for rel, data in originals.items():
            dst = root / rel
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
        for patch, _ in applied[-2:]:
            rejected_apply(root, patch)
        print("PASS duplicate application denied for both new candidates")
        mutations = (
            ("inherited denied", "infra/su_mount_ns.c", "case KSU_NS_INHERITED:\n        return 0;", "case KSU_NS_INHERITED:\n        return -EINVAL;"),
            ("unsupported namespace admitted", "infra/su_mount_ns.c", "return -EOPNOTSUPP;", "return 0;"),
            ("invalid namespace admitted", "infra/su_mount_ns.c", "default:\n        return -EINVAL;", "default:\n        return 0;"),
            ("admission bypassed", "policy/app_profile.c", "ret = ksu_mount_ns_precommit_status(profile->namespaces);", "ret = 0;"),
            ("admission guard bypassed", "policy/app_profile.c", "ret = ksu_mount_ns_precommit_status(profile->namespaces);\n    if (ret)", "ret = ksu_mount_ns_precommit_status(profile->namespaces);\n    if (false)"),
            ("profile SELinux status ignored", "policy/app_profile.c", "ret = setup_selinux(profile->selinux_domain, cred);", "setup_selinux(profile->selinux_domain, cred);"),
            ("profile SELinux guard bypassed", "policy/app_profile.c", "ret = setup_selinux(profile->selinux_domain, cred);\n    if (ret)", "ret = setup_selinux(profile->selinux_domain, cred);\n    if (false)"),
            ("init abort removed", "policy/app_profile.c", "if (ret) {\n        abort_creds(cred);", "if (ret) {"),
            ("init exact error lost", "policy/app_profile.c", "abort_creds(cred);\n        return ret;", "abort_creds(cred);\n        return -EINVAL;"),
            ("profile cleanup removed", "policy/app_profile.c", "if (profile)\n        ksu_put_root_profile(profile);", "if (profile)\n        ;"),
            ("credential abort removed", "policy/app_profile.c", "    abort_creds(cred);\n    return ret;", "    return ret;"),
            ("postcommit namespace restored", "policy/app_profile.c", "/* The admitted inherited mode needs no post-commit namespace operation. */", "setup_mount_ns(profile->namespaces);"),
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
    print("SOURCE-ONLY admission/status PASS; namespace transactions/integration/runtime/release remain BLOCKED")


if __name__ == "__main__":
    main()
