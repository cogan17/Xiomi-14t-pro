#!/usr/bin/env python3
"""Integrate exactly ONE pinned root driver into an isolated Rothko BSP checkout.

Does not execute upstream setup.sh and does not alter source baseline branches.
Fail closed on mismatched commits or existing KSU integration. No SUSFS patch,
NoMount, flashable images, ABI bypass or system device actions.
"""
import argparse
from pathlib import Path
import re
import subprocess

ROOT_REVISIONS = {
    "KernelSU-Next": ("KernelSU-Next/KernelSU-Next", "02a9e1c5fb2c4fd8117429fe004136332788c1b6"),
    "BakaSU": ("Baka-SU/BakaSU", "f6cb7e70c10ebde149f3121ae68b945514fd0801"),
}


def install(tree: Path, driver: Path) -> None:
    """Patch build references, not driver code; source pin validation is done in main."""
    tree = tree.resolve()
    driver = driver.resolve()
    kernel_dir = driver / "kernel"
    if not (kernel_dir / "Kconfig").is_file() or not (kernel_dir / "Makefile").is_file():
        raise ValueError("Missing root driver kernel/Kconfig or kernel/Makefile")
    if not re.search(r"(?m)^config\s+KSU\s*$", (kernel_dir / "Kconfig").read_text()):
        raise ValueError("Expected root Kconfig symbol CONFIG_KSU not found")
    makefile = tree / "drivers/Makefile"
    kconfig = tree / "drivers/Kconfig"
    if not makefile.is_file() or not kconfig.is_file():
        raise ValueError("Kernel drivers/Kconfig or drivers/Makefile missing")
    output = tree / "drivers/kernelsu"
    if output.exists() or output.is_symlink():
        raise ValueError("A root driver is already present: refuse to mix drivers")
    original_make = makefile.read_text(encoding="utf-8")
    original_kconfig = kconfig.read_text(encoding="utf-8")
    if "kernelsu/" in original_make.lower() or 'drivers/kernelsu/Kconfig' in original_kconfig:
        raise ValueError("Existing KSU entries; refusing duplicate or mixed integration")
    matches = list(re.finditer(r"(?m)^endmenu\s*$", original_kconfig))
    if not matches:
        raise ValueError("drivers/Kconfig has no endmenu; manual review required")
    endmenu = matches[-1]
    new_kconfig = (
        original_kconfig[:endmenu.start()]
        + 'source "drivers/kernelsu/Kconfig"\n'
        + original_kconfig[endmenu.start():]
    )
    # Apply only after static checks; roll back any partial integration on failure.
    import os
    try:
        makefile.write_text(
            original_make.rstrip() + "\n\nobj-$(CONFIG_KSU) += kernelsu/\n",
            encoding="utf-8",
        )
        kconfig.write_text(new_kconfig, encoding="utf-8")
        output.symlink_to(os.path.relpath(kernel_dir, output.parent), target_is_directory=True)
        if not output.joinpath("Kconfig").is_file():
            raise ValueError("Integration symlink failed")
    except Exception as original_error:
        # Attempt every rollback action even if an earlier cleanup step fails.
        # A failed rollback is never reported as a clean installation failure.
        rollback_errors = []
        for action in (
            lambda: output.unlink() if output.is_symlink() else None,
            lambda: makefile.write_text(original_make, encoding="utf-8"),
            lambda: kconfig.write_text(original_kconfig, encoding="utf-8"),
        ):
            try:
                action()
            except OSError as error:
                rollback_errors.append(error)
        if rollback_errors:
            raise RuntimeError(
                f"Root integration failed and rollback was incomplete: {rollback_errors!r}"
            ) from original_error
        raise


def verify_baseline(tree: Path) -> None:
    mk = (tree / "Makefile").read_text()
    assignments = {}
    for name in ("VERSION", "PATCHLEVEL", "SUBLEVEL"):
        match = re.search(r"(?m)^" + name + r"\s*=\s*(\d+)\s*$", mk)
        if not match:
            raise ValueError("Missing kernel version: " + name)
        assignments[name] = int(match.group(1))
    if tuple(assignments.values()) != (6, 1, 57):
        raise ValueError("Expected Xiaomi 6.1.57 source, do not relabel to GKI")
    common = (tree / "build.config.common").read_text()
    if not re.search(r"(?m)^KMI_GENERATION=11\s*$", common):
        raise ValueError("Unexpected KMI generation: refusing root patch")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", required=True, choices=sorted(ROOT_REVISIONS))
    p.add_argument("--tree", required=True, type=Path)
    p.add_argument("--upstream-checkout", required=True, type=Path)
    args = p.parse_args()
    tree = args.tree.resolve()
    driver = args.upstream_checkout.resolve()
    verify_baseline(tree)
    repo, pinned = ROOT_REVISIONS[args.root]
    actual = subprocess.check_output(
        ["git", "-C", str(driver), "rev-parse", "HEAD"], text=True
    ).strip()
    if actual != pinned:
        raise SystemExit(f"::error::{args.root} pin mismatch: {actual} != {pinned}")
    remote = subprocess.check_output(
        ["git", "-C", str(driver), "remote", "get-url", "origin"], text=True
    ).strip()
    if remote.rstrip("/").removesuffix(".git") != "https://github.com/" + repo:
        raise SystemExit("::error::Root checkout repository URL differs from pinned source")
    install(tree, driver)
    print(f"Integrated {args.root} into isolated source checkout at {pinned}")
    print("No SUSFS/NoMount patch applied. No device ABI/flash approval.")


if __name__ == "__main__":
    main()
