#!/usr/bin/env python3
"""Pinned patch round-trip and source contract; no kernel build/runtime claim."""
from pathlib import Path
import re
import subprocess
import sys
import tempfile

PIN = "3438d6aa431f96a23f9e625bec3d53ce1fb14161"
NAMES = (
    "g1-selinux-return-contract", "shared-cred-status", "g5-cred-borrow-api",
    "g5-ready-repeat-setup-guard", "g5-selinux-ready-publication",
    "g5-initial-setup-serialization",
)
FILES = ("kernel/core/init.c", "kernel/include/ksu.h",
         "kernel/selinux/selinux.c", "kernel/selinux/selinux.h")


def run(*args, cwd):
    result = subprocess.run(args, cwd=cwd, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors="replace"))
    return result.stdout


def body(source, signature):
    start = source.index(signature + "\n{")
    end = source.index("\n}", start)
    return source[start:end + 2]


def ordered(source, *tokens):
    pos = 0
    for token in tokens:
        pos = source.index(token, pos) + len(token)


def contract(core, selinux, header):
    assert "static DEFINE_MUTEX(ksu_cred_setup_lock);" in core
    wrapper = body(core, "int setup_ksu_cred(void)")
    ordered(wrapper, "mutex_lock(&ksu_cred_setup_lock);",
            "ret = ksu_setup_cred_domain_locked();",
            "mutex_unlock(&ksu_cred_setup_lock);", "return ret;")
    assert "spin_lock" not in wrapper
    setup = body(selinux, "int ksu_setup_cred_domain_locked(void)")
    ordered(setup, "ret = ksu_ready_cred_setup_status();",
            "if (ret != -EAGAIN)", "return ret;", "if (!ksu_cred)",
            "ret = setup_selinux(KERNEL_SU_CONTEXT, ksu_cred);",
            "if (ret) {", "return ret;",
            "if (!is_task_ksu_domain(ksu_cred))", "return -EACCES;",
            "ret = ksu_publish_ready_cred();", "return 0;")
    stop = body(core, "void ksu_unpublish_cred(void)")
    ordered(stop, "mutex_lock(&ksu_cred_setup_lock);",
            "spin_lock_irqsave(&ksu_cred_lock, flags);",
            "ksu_cred_ready = false;", "ksu_cred_stopping = true;",
            "spin_unlock_irqrestore(&ksu_cred_lock, flags);",
            "mutex_unlock(&ksu_cred_setup_lock);")
    exit_body = body(core, "void __exit kernelsu_exit(void)")
    ordered(exit_body, "ksu_unpublish_cred();", "ksu_supercalls_exit();",
            "ksu_selinux_hide_exit();", "ksu_feature_exit();", "put_cred(ksu_cred);")
    borrow = body(core, "const struct cred *ksu_borrow_ready_cred(void)")
    ordered(borrow, "spin_lock_irqsave", "if (ksu_cred_ready && ksu_cred)",
            "borrowed = get_cred(ksu_cred);", "spin_unlock_irqrestore")
    assert "mutex_lock" not in borrow
    assert "int ksu_setup_cred_domain_locked(void);" in header
    assert len(re.findall(r"ksu_setup_cred_domain_locked\(\)", core)) == 1


def main():
    upstream = Path(sys.argv[1]).resolve()
    repo = Path(__file__).resolve().parents[1]
    assert run("git", "rev-parse", "HEAD", cwd=upstream).decode().strip() == PIN
    originals = {f: run("git", "show", PIN + ":" + f, cwd=upstream) for f in FILES}
    with tempfile.TemporaryDirectory(prefix="rothko-g5-setup-") as td:
        root = Path(td)
        run("git", "init", "-q", cwd=root)
        run("git", "config", "core.autocrlf", "false", cwd=root)
        for f, data in originals.items():
            dst = root / f
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(data)
        patches = []
        for i, name in enumerate(NAMES):
            # Normalize transport CRLF only; never recount or relax whitespace.
            patch = root / (name + ".patch")
            patch.write_bytes((repo / "patches" / ("rothko-ksun-" + name + "-candidate.patch"))
                              .read_bytes().replace(b"\r\n", b"\n"))
            flags = ["--unidiff-zero"] if i == 0 else []
            run("git", "apply", "--check", "--whitespace=error", *flags, str(patch), cwd=root)
            run("git", "apply", "--whitespace=error", *flags, str(patch), cwd=root)
            patches.append((patch, flags))
            print("PASS sequential apply:", name)
        core, selinux, header = ((root / f).read_text() for f in
                                 (FILES[0], FILES[2], FILES[3]))
        contract(core, selinux, header)
        mutations = (
            ("setup lock removed", core.replace("    mutex_lock(&ksu_cred_setup_lock);", "", 1), selinux),
            ("setup unlock removed", core.replace("    mutex_unlock(&ksu_cred_setup_lock);", "", 1), selinux),
            ("teardown lock removed", core.replace(body(core, "void ksu_unpublish_cred(void)"),
                body(core, "void ksu_unpublish_cred(void)").replace("    mutex_lock(&ksu_cred_setup_lock);", "")), selinux),
            ("teardown drain removed", core.replace("\tksu_unpublish_cred();", ""), selinux),
            ("READY guard bypassed", core, selinux.replace("if (ret != -EAGAIN)", "if (false)")),
            ("domain check bypassed", core, selinux.replace("if (!is_task_ksu_domain(ksu_cred))", "if (false)")),
            ("publication removed", core, selinux.replace("ret = ksu_publish_ready_cred();", "ret = 0;")),
        )
        for label, c, s in mutations:
            try:
                contract(c, s, header)
            except (AssertionError, ValueError):
                print("PASS rejected mutation:", label)
            else:
                raise AssertionError("undetected mutation: " + label)
        for patch, flags in reversed(patches):
            run("git", "apply", "--reverse", "--check", "--whitespace=error", *flags, str(patch), cwd=root)
            run("git", "apply", "--reverse", "--whitespace=error", *flags, str(patch), cwd=root)
        for f, data in originals.items():
            actual = (root / f).read_bytes()
            if actual != data:
                import difflib
                raise AssertionError(f + ": reverse mismatch\n" + "".join(difflib.unified_diff(
                    data.decode().splitlines(True), actual.decode().splitlines(True))))
        print("PASS reverse sequence: exact pinned bytes restored")
    print("SOURCE CONTRACT PASS; kernel runtime/integration/release remain BLOCKED")


if __name__ == "__main__":
    main()
