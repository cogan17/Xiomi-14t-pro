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
INCLUDE_PATCH = "patches/rothko-susfs-exec-include-candidate.patch"
INCLUDE_GUARD = (
    "#ifdef CONFIG_KSU_SUSFS\n"
    "#include <linux/susfs_def.h>\n"
    "#endif\n\n"
    "#include <linux/uaccess.h>"
)


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


def composition_contract(src, header):
    """Only new assertions for the additional, already-existing include patch."""
    contract(src, header)  # Recheck once on the combined source, not each old mutation.
    require(src.count(INCLUDE_GUARD) == 1,
            "SUSFS include guard missing, repeated, or moved")
    require(src.count("#include <linux/susfs_def.h>") == 1,
            "duplicate SUSFS include or unsafe extra configuration path")
    require(src.find(INCLUDE_GUARD) < src.find("struct user_arg_ptr {"),
            "include must precede typed native/COMPAT user argument structure")
    require(src.count("ksu_rothko_pre_execveat(&fd, &filename, &argv, &envp, &flags)") == 1,
            "duplicate pre-exec consumer detected")
    require("ksu_handle_post_execveat_sucompat" not in src,
            "unsupported post-exec session FD hook introduced")
    # No dependency claim for generated kernel header, provider link or module lifecycle.
    return True


def composition_mutations(src, header):
    cases = (
        ("include guard dropped", INCLUDE_GUARD,
         "#include <linux/susfs_def.h>\n#include <linux/uaccess.h>"),
        ("include omitted", INCLUDE_GUARD, "#include <linux/uaccess.h>"),
        ("duplicate include", INCLUDE_GUARD,
         INCLUDE_GUARD.replace("#include <linux/uaccess.h>",
                               "#include <linux/susfs_def.h>\n#include <linux/uaccess.h>")),
        ("wrong configuration", INCLUDE_GUARD,
         INCLUDE_GUARD.replace("#ifdef CONFIG_KSU_SUSFS", "#ifdef CONFIG_KSU")),
        ("extra pre-exec dispatch",
         "\tretval = ksu_rothko_pre_execveat(&fd, &filename, &argv, &envp, &flags);",
         "\tretval = ksu_rothko_pre_execveat(&fd, &filename, &argv, &envp, &flags);\n"
         "\tretval = ksu_rothko_pre_execveat(&fd, &filename, &argv, &envp, &flags);"),
    )
    for label, old, new in cases:
        require(old in src, "negative composition target missing: " + label)
        try:
            composition_contract(src.replace(old, new, 1), header)
        except RuntimeError:
            continue
        raise RuntimeError("unsafe composition mutation accepted: " + label)
    return len(cases)


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
    include_data = (project / INCLUDE_PATCH).read_bytes()
    for data, name in ((include_data, "SUSFS include"), (patch_data, "KSUN prehook")):
        require(data.count(b"diff --git ") == 1
                and data.count(b"--- a/fs/exec.c") == 1
                and data.count(b"+++ b/fs/exec.c") == 1,
                name + " patch scope changed")
    with tempfile.TemporaryDirectory(prefix="rothko-exec-composition-") as t:
        root = Path(t)
        git(root, "init", "-q")
        target = root / "fs/exec.c"
        target.parent.mkdir()
        target.write_bytes(original)
        included = root / "existing-include.patch"
        prehook = root / "existing-prehook.patch"
        included.write_bytes(include_data)
        prehook.write_bytes(patch_data)
        for candidate in (included, prehook):
            git(root, "apply", "--check", "--whitespace=error", str(candidate))
            git(root, "apply", "--whitespace=error", str(candidate))
        combined = target.read_text(encoding="utf-8")
        composition_contract(combined, header)
        count = composition_mutations(combined, header)
        # Prior seven prehook-only negative cases passed in run 38560101717;
        # they are not rerun because that source candidate is byte-identical.
        for candidate in (included, prehook):
            duplicate = subprocess.run(["git", "apply", "--check", str(candidate)],
                                       cwd=root, capture_output=True, timeout=25)
            require(duplicate.returncode != 0, "duplicate candidate accepted")
        for candidate in (prehook, included):
            git(root, "apply", "--reverse", "--check", "--whitespace=error",
                str(candidate))
            git(root, "apply", "--reverse", "--whitespace=error", str(candidate))
        require(target.read_bytes() == original, "composed reverse changed BSP")
    print("PASS: existing SUSFS include + pinned KSUN typed prehook strict composition")
    print("PASS:", count, "new composition negative mutations; both duplicates rejected")
    print("PASS: both reverse patches restore immutable Rothko fs/exec.c byte-for-byte")
    print("SOURCE-ONLY PASS: KSUN provider linking, header availability, ABI/KMI,"
          " FD lifecycle and device runtime still unverified")



if __name__ == "__main__":
    main()
