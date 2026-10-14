#!/usr/bin/env python3
"""Read-only KSUN/SUSFS provider identity gate; never installs or builds."""
import argparse
import json
import re
import subprocess
from pathlib import Path

PROVIDER_REMOTE = "https://github.com/pershoot/KernelSU-Next"
PROVIDER_SHA = "3438d6aa431f96a23f9e625bec3d53ce1fb14161"
VANILLA_SHA = "02a9e1c5fb2c4fd8117429fe004136332788c1b6"
BSP_REQUIRED = ("fs/susfs.c", "include/linux/susfs.h", "include/linux/susfs_def.h")
SESSION_BLOCKER = "SU session identity, post-exec authorization and FD lifetime not proven"


class GateError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise GateError(message)


def git_value(directory, *arguments):
    result = subprocess.run(["git", "-C", str(directory), *arguments],
                            capture_output=True, text=True, timeout=20, check=False)
    require(result.returncode == 0, "Git provider identity could not be verified")
    return result.stdout.strip()


def read(root, path):
    target = root / path
    require(target.is_file() and not target.is_symlink(), "Missing/linked source: " + path)
    return target.read_text(encoding="utf-8")


def compact(value):
    return re.sub(r"\s+", " ", value)


def verify_provider(checkout):
    checkout = Path(checkout).resolve()
    head = git_value(checkout, "rev-parse", "HEAD")
    remote = git_value(checkout, "remote", "get-url", "origin")
    remote = remote.rstrip("/").removesuffix(".git")
    require(head != VANILLA_SHA, "Vanilla KSUN pin must not serve the SUSFS prehook")
    require(head == PROVIDER_SHA, "SUSFS provider SHA mismatch")
    require(remote == PROVIDER_REMOTE, "SUSFS provider remote mismatch")
    config = read(checkout, "kernel/Kconfig")
    kbuild = read(checkout, "kernel/Kbuild")
    header = read(checkout, "kernel/feature/sucompat.h")
    implementation = read(checkout, "kernel/feature/sucompat.c")
    stanza = re.search(r"(?ms)^config KSU_SUSFS\n(.*?)(?=^config |^endmenu|\Z)", config)
    require(stanza is not None, "CONFIG_KSU_SUSFS missing")
    require(all(re.search(r"(?m)^\s*depends on " + re.escape(x) + r"\s*$", stanza.group(1))
                for x in ("KSU", "THREAD_INFO_IN_TASK")), "SUSFS Kconfig dependencies changed")
    require(re.search(r"(?m)^kernelsu-objs\s*\+=\s*feature/sucompat\.o\s*$", kbuild),
            "KSUN prehook provider object missing from Kbuild")
    require(re.search(r"(?m)^obj-\$\(CONFIG_KSU\)\s*\+=\s*kernelsu\.o\s*$", kbuild),
            "Kbuild lacks CONFIG_KSU object selection")
    signature = ("int ksu_handle_execveat(int *fd, struct filename **filename_ptr, "
                 "void *argv, void *envp, int *flags)")
    require(compact(signature) + ";" in compact(header), "Pinned prehook declaration mismatch")
    require(compact(signature) in compact(implementation), "Pinned prehook definition missing")
    require("#ifdef CONFIG_KSU_SUSFS" in header and "#ifdef CONFIG_KSU_SUSFS" in implementation,
            "SUSFS implementation guards missing")
    return {"provider_pin": head, "provider_source_contract": "verified"}


def inspect(checkout, bsp):
    evidence = verify_provider(checkout)
    bsp = Path(bsp).resolve()
    makefile = read(bsp, "Makefile")
    config = read(bsp, "build.config.common")
    for key, value in (("VERSION", "6"), ("PATCHLEVEL", "1"), ("SUBLEVEL", "57")):
        require(re.search(r"(?m)^" + key + r"\s*=\s*" + value + r"\s*$", makefile),
                "BSP kernel version differs from reviewed 6.1.57")
    require(re.search(r"(?m)^KMI_GENERATION=11\s*$", config), "BSP KMI metadata changed")
    missing = [name for name in BSP_REQUIRED if not (bsp / name).is_file()]
    evidence.update({
        "integration_ready": False,
        "status": "SOURCE_ONLY_PROVIDER_OK__BUILD_HOLD",
        "missing_susfs_bsp_files": missing,
        "blocking_gates": [SESSION_BLOCKER,
                           "Verified built-in KSU/SUSFS Kconfig and kernel linker proof missing",
                           "Device identity, ABI/KMI, kernel build and runtime remain unverified"],
    })
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider-checkout", type=Path, required=True)
    parser.add_argument("--bsp-tree", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        result = inspect(arguments.provider_checkout, arguments.bsp_tree)
    except (GateError, OSError) as error:
        parser.exit(2, "SUSFS provider rejected: " + str(error) + "\n")
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
