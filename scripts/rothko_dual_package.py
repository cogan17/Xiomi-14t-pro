#!/usr/bin/env python3
"""Build *candidate-only* Rothko AK3 and boot.img from one kernel Image.

Requires a locally supplied, matching STOCK Rothko boot.img, a trusted
magiskboot binary and an audited local AnyKernel3 checkout. Never flashes,
publishes, or marks a package compatible. The output is blocked by design.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

ROOTS = {"KernelSU", "KernelSU-Next", "BakaSU"}
BOOT_MAGIC = b"ANDROID!"
ARM64_MAGIC = b"ARM\x64"

AK3_SCRIPT = """### Cogan Rothko AnyKernel3 -- DEVELOPMENT CANDIDATE
properties() { '
kernel.string=Cogan Rothko - UNAPPROVED CANDIDATE
do.devicecheck=1
do.modules=0
do.systemless=1
do.cleanup=1
do.cleanuponabort=0
device.name1=rothko
supported.versions=16
'; }
BLOCK=boot
IS_SLOT_DEVICE=1
RAMDISK_COMPRESSION=auto
PATCH_VBMETA_FLAG=0
. tools/ak3-core.sh
abort "Rothko candidate only: ABI/KMI/device compatibility unapproved. Do NOT flash."
# After device evidence and separately reviewed release approval only:
# split_boot
# flash_boot
"""


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def validate_image(path: Path, *, kernel: bool) -> None:
    if not path.is_file():
        raise ValueError(f"Missing image: {path}")
    size = path.stat().st_size
    if not (1024 * 1024 <= size <= 256 * 1024 * 1024):
        raise ValueError(f"Unexpected image size ({size} bytes): {path}")
    with path.open("rb") as stream:
        if kernel:
            stream.seek(0x38)
            if stream.read(4) != ARM64_MAGIC:
                raise ValueError("Expected an ARM64 uncompressed Image; not a ZIP or boot.img")
        elif stream.read(8) != BOOT_MAGIC:
            raise ValueError("Not an Android boot.img (ANDROID! header missing)")


def run_magiskboot(binary: Path, *args: str, cwd: Path) -> None:
    result = subprocess.run([str(binary), *args], cwd=cwd,
                            capture_output=True, text=True, timeout=180)
    if result.returncode:
        raise RuntimeError(f"magiskboot {args[0]} failed ({result.returncode}): "
                           f"{result.stderr[-2000:]}")


def repack_and_verify(binary: Path, stock: Path, image: Path, target: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="rothko-boot-") as tmp:
        wd = Path(tmp)
        original = wd / "stock_boot.img"
        shutil.copyfile(stock, original)
        run_magiskboot(binary, "unpack", original.name, cwd=wd)
        extracted = wd / "kernel"
        if not extracted.is_file():
            raise RuntimeError("magiskboot did not extract the kernel; refusing to repack")
        shutil.copyfile(image, extracted)
        run_magiskboot(binary, "repack", original.name, cwd=wd)
        repacked = wd / "new-boot.img"
        validate_image(repacked, kernel=False)
        # Validate embedded payload, not merely boot header and exit code.
        check = wd / "verify"
        check.mkdir()
        shutil.copyfile(repacked, check / "boot.img")
        run_magiskboot(binary, "unpack", "boot.img", cwd=check)
        embedded = check / "kernel"
        if not embedded.exists() or sha256(embedded) != sha256(image):
            raise RuntimeError("Repacked boot.img kernel does not match the AK3 Image")
        shutil.copyfile(repacked, target)


def package_ak3(template: Path, image: Path, dest: Path) -> None:
    required = (
        template / "tools" / "ak3-core.sh",
        template / "META-INF" / "com" / "google" / "android" / "update-binary",
    )
    if any(not p.is_file() for p in required):
        raise ValueError("AnyKernel3 template is incomplete (core/update-binary missing)")
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=6) as archive:
        for name in ("tools", "META-INF"):
            for path in sorted((template / name).rglob("*")):
                if path.is_symlink():
                    raise ValueError("Symlink in AK3 template not allowed")
                if path.is_file():
                    rel = path.relative_to(template).as_posix()
                    archive.write(path, rel)
        archive.write(image, "Image")
        archive.writestr("anykernel.sh", AK3_SCRIPT)
        archive.writestr("UNAPPROVED-CANDIDATE.txt",
                         "DO NOT FLASH. ABI/KMI and device compatibility remain unverified.\n")
    with zipfile.ZipFile(dest) as archive:
        bad = archive.testzip()
        if bad is not None:
            raise RuntimeError("ZIP CRC test failed: " + bad)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kernel-image", type=Path, required=True)
    parser.add_argument("--stock-boot", type=Path, required=True)
    parser.add_argument("--magiskboot", type=Path, required=True)
    parser.add_argument("--ak3-template", type=Path, required=True)
    parser.add_argument("--root", choices=sorted(ROOTS), required=True)
    parser.add_argument("--firmware", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.firmware.startswith("OS3.") or not args.firmware.endswith(".WNNIDXM"):
        parser.error("Firmware must be a Rothko WNNIDXM OS3 build")
    if len(args.source_commit) != 40 or any(c not in "0123456789abcdef" for c in args.source_commit):
        parser.error("Specify the full, lowercase 40-character source commit SHA")
    validate_image(args.kernel_image, kernel=True)
    validate_image(args.stock_boot, kernel=False)
    if not args.magiskboot.is_file():
        parser.error("Provide a locally verified magiskboot binary")
    if args.output.exists():
        parser.error("Output directory must not exist (prevent overwriting backups)")
    args.output.mkdir(parents=True)
    try:
        boot = args.output / "boot.img"
        ak3 = args.output / "Cogan-Rothko-AK3-UNAPPROVED.zip"
        repack_and_verify(args.magiskboot.resolve(), args.stock_boot, args.kernel_image, boot)
        package_ak3(args.ak3_template, args.kernel_image, ak3)
        manifest = {
            "schema": 1,
            "device": "rothko",
            "firmware": args.firmware,
            "partition": "boot",
            "root": args.root,
            "source_commit": args.source_commit,
            "approved_for_flash": False,
            "stock_boot_sha256": sha256(args.stock_boot),
            "kernel_image_sha256": sha256(args.kernel_image),
            "boot_img_sha256": sha256(boot),
            "ak3_zip_sha256": sha256(ak3),
            "note": "Both derived from same Image. NOT compatible/flashable until separately approved.",
        }
        (args.output / "candidate-manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        print("CANDIDATES CREATED, BUT NOT APPROVED FOR FLASH:", args.output)
        print("boot.img:", manifest["boot_img_sha256"])
        print("AK3 ZIP:", manifest["ak3_zip_sha256"])
    except BaseException:
        # Do not leave partial boot.img or AK3 ZIP that could be mistaken for a release.
        shutil.rmtree(args.output, ignore_errors=True)
        raise


if __name__ == "__main__":
    main()
