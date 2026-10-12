#!/usr/bin/env bash
# Real kernel source compile, but generic GKI config only.
# NO root patching, module integration, AK3, boot.img, or flashing.
set -euo pipefail
case "$1" in
  provenance)
    python3 - <<'PY'
from pathlib import Path
import re
make = Path("Makefile").read_text()
config = Path("build.config.common").read_text()
def field(text, key):
    match = re.search(r"(?m)^"+re.escape(key)+r"\s*=\s*(\d+)\s*$", text)
    if not match:
        raise SystemExit("Missing source provenance: " + key)
    return int(match.group(1))
version = tuple(field(make, key) for key in ("VERSION", "PATCHLEVEL", "SUBLEVEL"))
if version != (6, 1, 57):
    raise SystemExit(f"Expected audited Xiaomi BSP 6.1.57, got {version}")
if field(config, "KMI_GENERATION") != 11:
    raise SystemExit("Expected KMI generation 11")
if not Path("arch/arm64/configs/gki_defconfig").is_file():
    raise SystemExit("Missing GKI ARM64 defconfig")
print("PASS: Xiaomi source 6.1.57, KMI generation 11, and GKI defconfig")
PY
    ;;
  compile)
    bash scripts/rothko_bsp_compile_smoke.sh provenance
    if [[ "$ARCH" != arm64 || "$LLVM" != 1 ]]; then
      echo "::error::Expected ARCH=arm64 and LLVM=1" >&2
      exit 1
    fi
    command -v clang
    command -v ld.lld
    mkdir -p out
    echo "Generating generic GKI config (NOT Rothko board defconfig)"
    make O=out ARCH=arm64 LLVM=1 LLVM_IAS=1 gki_defconfig
    if grep -Eq '^CONFIG_(KSU|KSU_SUSFS)=y' out/.config; then
      echo "::error::No root variants permitted in this stock source smoke compile." >&2
      exit 1
    fi
    echo "Compiling ARM64 Image from actual Xiaomi 6.1.57 BSP source"
    make -j2 O=out ARCH=arm64 LLVM=1 LLVM_IAS=1 Image
    test -s out/arch/arm64/boot/Image
    ;;
  *)
    echo "Usage: bash scripts/rothko_bsp_compile_smoke.sh {provenance|compile}" >&2
    exit 2
    ;;
esac
