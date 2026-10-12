#!/usr/bin/env python3
"""Integrate pinned NoMount source into ONE isolated Rothko BSP checkout.

No phone, ZIP, root manager, release, flashing or disabled ABI/version checks.
NoMount source is taken from reviewed commit; do not execute upstream setup.sh.
"""

from pathlib import Path
import argparse
import os
import re
import subprocess

UPSTREAM = "https://github.com/maxsteeel/nomount"
PIN = "8005194827ca3edc7e75b9523a874307b2c3e883"


def audit_baseline(tree: Path) -> None:
    source = (tree / "Makefile").read_text(encoding="utf-8")
    version = []
    for key in ("VERSION", "PATCHLEVEL", "SUBLEVEL"):
        match = re.search(r"(?m)^" + key + r"\s*=\s*(\d+)\s*$", source)
        if match is None:
            raise ValueError("Missing kernel version field " + key)
        version.append(int(match.group(1)))
    if version != [6, 1, 57]:
        raise ValueError(f"Expected audited Xiaomi BSP 6.1.57, not {version}")
    if not re.search(r"(?m)^KMI_GENERATION=11\s*$",
                     (tree / "build.config.common").read_text(encoding="utf-8")):
        raise ValueError("KMI generation mismatch")


def integrate(tree: Path, src: Path) -> None:
    tree, src = tree.resolve(), src.resolve()
    source_dir = src / "kernel/src"
    if not (source_dir / "Kconfig").is_file() or not (source_dir / "Makefile").is_file():
        raise ValueError("NoMount upstream kernel/src is incomplete")
    if not re.search(r"(?m)^config NOMOUNT\s*$",
                     (source_dir / "Kconfig").read_text(encoding="utf-8")):
        raise ValueError("CONFIG_NOMOUNT missing from source")
    if not (source_dir / "nomount.c").is_file():
        raise ValueError("NoMount C source is missing")

    fs_makefile = tree / "fs/Makefile"
    fs_kconfig = tree / "fs/Kconfig"
    if not fs_makefile.is_file() or not fs_kconfig.is_file():
        raise ValueError("Missing kernel fs/Makefile or fs/Kconfig")
    make_text = fs_makefile.read_text(encoding="utf-8")
    config_text = fs_kconfig.read_text(encoding="utf-8")
    target = tree / "fs/nomount"
    if target.exists() or target.is_symlink():
        raise ValueError("NoMount already present, refusing duplicate integration")
    if "CONFIG_NOMOUNT" in make_text or 'fs/nomount/Kconfig' in config_text:
        raise ValueError("NoMount Kbuild references already present")
    endmenus = list(re.finditer(r"(?m)^endmenu\s*$", config_text))
    if not endmenus:
        raise ValueError("No endmenu in fs/Kconfig; manual review needed")
    anchor = endmenus[-1].start()
    config_updated = (config_text[:anchor] +
                      'source "fs/nomount/Kconfig"\n' +
                      config_text[anchor:])
    target.symlink_to(os.path.relpath(source_dir, target.parent), target_is_directory=True)
    fs_makefile.write_text(
        make_text.rstrip() + "\n\nobj-$(CONFIG_NOMOUNT) += nomount/\n",
        encoding="utf-8"
    )
    fs_kconfig.write_text(config_updated, encoding="utf-8")
    if not (target / "nomount.c").is_file():
        raise ValueError("NoMount integration symlink could not be resolved")
    print("Integrated pinned NoMount into the isolated checkout (no flash)")


def audit_checkout(src: Path) -> None:
    actual = subprocess.check_output(
        ["git", "-C", str(src), "rev-parse", "HEAD"], text=True
    ).strip()
    if actual != PIN:
        raise ValueError(f"NoMount revision mismatch, expected {PIN}, got {actual}")
    url = subprocess.check_output(
        ["git", "-C", str(src), "remote", "get-url", "origin"], text=True
    ).strip().removesuffix(".git").rstrip("/")
    if url != UPSTREAM:
        raise ValueError(f"Unexpected NoMount upstream: {url}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree", type=Path, required=True)
    parser.add_argument("--upstream-checkout", type=Path, required=True)
    args = parser.parse_args()
    tree = args.tree.resolve()
    src = args.upstream_checkout.resolve()
    audit_baseline(tree)
    audit_checkout(src)
    integrate(tree, src)


if __name__ == "__main__":
    main()
