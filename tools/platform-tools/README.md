# Rothko: AK3 ZIP + Platform-Tools boot.img (development)

One compiled ARM64 `Image` can feed **two candidate formats**:
`Cogan-Rothko-AK3-UNAPPROVED.zip` (AnyKernel3) and `boot.img`
(Windows CMD + official Android SDK Platform-Tools).
No automatic release or flash is possible yet.

## Build candidates locally, not on phone
Use a **matching, authentic Rothko stock boot.img** (not Degas), a
trusted `magiskboot` executable and a locally reviewed AnyKernel3
template with `tools/ak3-core.sh` and `META-INF/com/google/android/update-binary`:

```sh
python3 scripts/rothko_dual_package.py \
  --kernel-image /path/to/Image --stock-boot /path/to/rothko-stock-boot.img \
  --magiskboot /path/to/magiskboot --ak3-template /path/to/AnyKernel3 \
  --root BakaSU --firmware OS3.0.301.0.WNNIDXM \
  --source-commit FULL_40_CHARACTER_LOWERCASE_SHA \
  --output ./rothko-candidate
```

The program repacks stock `boot.img`, re-extracts the embedded kernel
and compares its SHA-256 against the identical `Image` placed in AK3.
The manifest records hashes and **`approved_for_flash=false`**.

## Windows CMD Platform-Tools preflight

Place `fastboot.exe` in PATH or next to the scripts, then use:

```bat
tools\platform-tools\flash-rothko.cmd -Image "C:\Rothko\boot.img" -Manifest "C:\Rothko\candidate-manifest.json"
```

The script checks manifest/hash/header, fastboot product `rothko`,
active Slot A, unlocked bootloader, and bootloader mode. It only
supports `boot_a`, never touches `init_boot`, `vbmeta` or Slot B.
**Candidate manifests refuse to flash even if `-Flash` is supplied.**

**Important:** fastboot product/version alone cannot verify firmware,
vendor module ABI/KMI, secure boot signatures, or actual root behavior.
AK3 similarly contains a deliberate blocking `abort`. Both outputs
are **non-flashable development candidates** until device-specific
build, ABI validation, recovery plan, and release approval are proven.
A future separately reviewed release will need to unlock these gates.
