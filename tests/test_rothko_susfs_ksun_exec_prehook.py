#!/usr/bin/env python3
"""Source-only Rothko KSUN pre-exec consumer; no build, runtime, or flash."""
from pathlib import Path
import re
import subprocess
import sys
import tempfile

BSP_BLOB = "ef93a4d5911b48f2052f5130092e9c46b2d0262b"
PIN = "3438d6aa431f96a23f9e625bec3d53ce1fb14161"
PATCH = "patches/rothko-susfs-ksun-exec-prehook-candidate.patch"


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def git(root, *args):
    p = subprocess.run(["git", *args], cwd=root, capture_output=True, timeout=25)
    require(p.returncode == 0, p.stderr.decode(errors="replace"))
    return p.stdout.decode().strip()


def contract(src, header):
    normalized = lambda s: re.sub(r"\s+", " ", s)
    signature = ("int ksu_handle_execveat(int *fd, struct filename **filename_ptr,"
                 " void *argv, void *envp, int *flags);")
    require(normalized(signature) in normalized(header), "pinned provider ABI changed")
    require(normalized("extern " + signature) in normalized(src)
            and src.count("extern int ksu_handle_execveat(") == 1,
            "BSP prototype mismatch/duplicate")
    require(src.count("#ifdef CONFIG_KSU_SUSFS\n/* Match the pinned KSUN") == 1,
            "missing feature gate")
    adapter = src.split("static int ksu_rothko_pre_execveat(", 1)
    require(len(adapter) == 2, "typed adapter absent")
    adapter_body = adapter[1].split("\n}", 1)[0]
    require("struct user_arg_ptr *argv" in adapter_body
            and "struct user_arg_ptr *envp" in adapter_body,
            "native/COMPAT typing missing")
    require("return ksu_handle_execveat(fd, filename, argv, envp, flags);" in adapter_body,
            "KSUN result or args discarded")
    require(adapter[1].split("\n}", 1)[1].startswith("\n#endif\n"),
            "adapter not protected by CONFIG_KSU_SUSFS")
    fn = src.split("static int do_execveat_common(", 1)
    require(len(fn) == 2, "BSP exec path missing")
    body = fn[1].split("\nint kernel_execve(", 1)[0]
    gate = ("#ifdef CONFIG_KSU_SUSFS\n"
            "\tretval = ksu_rothko_pre_execveat(&fd, &filename, &argv, &envp, &flags);\n"
            "\tif (retval < 0)\n\t\tgoto out_ret;\n#endif")
    require(body.count(gate) == 1, "negative errno / native/COMPAT contract broken")
    require(body.find("if (IS_ERR(filename))") < body.find(gate)
            < body.find("bprm = alloc_bprm("), "hook not before allocation")
    require(body.count("bprm = alloc_bprm(") == 1, "duplicate allocation")
    require(body.count("out_ret:\n\tputname(filename);\n\treturn retval;") == 1,
            "error cleanup/filename ownership lost")
    require(src.count("return do_execveat_common(") >= 4
            and src.count(".is_compat = true") >= 4,
            "native/COMPAT entry selection changed")


def mutations(src, header):
    cases = (
        ("swallow error", "\tif (retval < 0)\n\t\tgoto out_ret;",
         "\tif (retval < -4096)\n\t\tgoto out_ret;"),
        ("wrong argv pointer", "&fd, &filename, &argv, &envp, &flags",
         "&fd, &filename, argv.ptr.native, &envp, &flags"),
        ("wrong envp pointer", "&fd, &filename, &argv, &envp, &flags",
         "&fd, &filename, &argv, envp.ptr.native, &flags"),
        ("missing putname", "out_ret:\n\tputname(filename);", "out_ret:\n\t/* removed */"),
        ("gate bypass", "#ifdef CONFIG_KSU_SUSFS\n\tretval", "#if 1\n\tretval"),
        ("void adapter", "static int ksu_rothko_pre_execveat(", "static void ksu_rothko_pre_execveat("),
        ("stubbed adapter", "\treturn ksu_handle_execveat(fd, filename, argv, envp, flags);",
         "\treturn 0;"),
    )
    for label, old, new in cases:
        require(old in src, "mutation target missing: " + label)
        try:
            contract(src.replace(old, new, 1), header)
        except RuntimeError:
            continue
        raise RuntimeError("mutation accepted: " + label)
    return len(cases)


def main():
    require(len(sys.argv) == 3, "usage: test_rothko_susfs_ksun_exec_prehook.py BSP_TREE KSUN_TREE")
    project = Path(__file__).resolve().parents[1]
    bsp = Path(sys.argv[1]).resolve()
    ksun = Path(sys.argv[2]).resolve()
    require(git(ksun, "rev-parse", "HEAD") == PIN, "wrong KSUN pin")
    require(git(bsp, "hash-object", "fs/exec.c") == BSP_BLOB, "BSP blob changed")
    original = (bsp / "fs/exec.c").read_bytes()
    header = (ksun / "kernel/feature/sucompat.h").read_text()
    patch_data = (project / PATCH).read_bytes()
    require(patch_data.count(b"diff --git ") == 1, "patch touches other files")
    with tempfile.TemporaryDirectory(prefix="rothko-exec-consumer-") as t:
        root = Path(t)
        git(root, "init", "-q")
        target = root / "fs/exec.c"
        target.parent.mkdir()
        target.write_bytes(original)
        patch = root / "candidate.patch"
        patch.write_bytes(patch_data)
        git(root, "apply", "--check", "--whitespace=error", str(patch))
        git(root, "apply", "--whitespace=error", str(patch))
        src = target.read_text()
        contract(src, header)
        count = mutations(src, header)
        duplicate = subprocess.run(["git", "apply", "--check", str(patch)],
                                   cwd=root, capture_output=True, timeout=25)
        require(duplicate.returncode != 0, "duplicate patch accepted")
        git(root, "apply", "--reverse", "--check", "--whitespace=error", str(patch))
        git(root, "apply", "--reverse", "--whitespace=error", str(patch))
        require(target.read_bytes() == original, "reverse failed to restore source")
    print("PASS: pinned Rothko BSP / KSUN prehook signature; typed native/COMPAT errno cleanup")
    print("PASS:", count, "negative mutations, duplicate rejected, byte-identical reverse")
    print("SOURCE-ONLY PASS: no compile, ABI/KMI, FD lifetime, device, or release proof")


if __name__ == "__main__":
    main()
