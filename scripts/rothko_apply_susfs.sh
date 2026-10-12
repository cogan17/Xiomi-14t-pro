#!/usr/bin/env bash
# Apply Simonpunk's 6.1 SUSFS *kernel-side* patch to disposable CI source.
# BakaSU has its own SUSFS integration: NEVER apply upstream KernelSU driver
# patch blindly. Refuse any patch fuzz, backup/reject file or version bypass.
set -euo pipefail
if (( $# != 2 )); then
  echo "Usage: rothko_apply_susfs.sh <kernel-tree> <checked-out-susfs-tree>" >&2
  exit 2
fi
tree="$(realpath "$1")"
susfs="$(realpath "$2")"

[[ -f "$tree/Makefile" && -f "$tree/fs/Kconfig" && -f "$tree/fs/Makefile" ]] || {
  echo "::error::Invalid Rothko kernel source"; exit 1;
}
[[ -f "$tree/drivers/kernelsu/Kconfig" && -f "$tree/fs/nomount/Kconfig" ]] || {
  echo "::error::BakaSU + NoMount not integrated in same source"; exit 1;
}
grep -Eq '^config[[:space:]]+KSU_SUSFS$' "$tree/drivers/kernelsu/Kconfig" || {
  echo "::error::BakaSU does not contain expected native SUSFS integration"; exit 1;
}
[[ -f "$tree/build.config.common" ]] || exit 1
grep -qx 'KMI_GENERATION=11' "$tree/build.config.common" || {
  echo "::error::KMI generation mismatch"; exit 1;
}
grep -Eq '^VERSION = 6$' "$tree/Makefile" &&
grep -Eq '^PATCHLEVEL = 1$' "$tree/Makefile" &&
grep -Eq '^SUBLEVEL = 57$' "$tree/Makefile" || {
  echo "::error::Expected actual Xiaomi BSP 6.1.57"; exit 1;
}

# Initial upstream observation is a SHORT GitLab commit prefix. Reject an
# upstream branch update; DO NOT silently fetch latest in production builds.
[[ "$SUSFS_EXPECTED_PREFIX" =~ ^[a-f0-9]{8,40}$ ]] || {
  echo "::error::Invalid expected SUSFS revision prefix"; exit 1;
}
actual="$(git -C "$susfs" rev-parse HEAD)"
remote="$(git -C "$susfs" remote get-url origin)"
[[ "$remote" == "https://gitlab.com/simonpunk/susfs4ksu.git" ]] || {
  echo "::error::SUSFS source must be the official Simonpunk GitLab"; exit 1;
}
[[ "$actual" == "$SUSFS_EXPECTED_PREFIX"* ]] || {
  echo "::error::Upstream SUSFS revision changed ($actual). Stop for repin and code review."; exit 1;
}
echo "Simonpunk GitLab commit: $actual"

patchfile="$susfs/kernel_patches/50_add_susfs_in_gki-android14-6.1.patch"
[[ -s "$patchfile" && -s "$susfs/kernel_patches/fs/susfs.c" &&
   -s "$susfs/kernel_patches/include/linux/susfs.h" ]] || {
  echo "::error::Expected SUSFS 6.1 patch or sources missing"; exit 1;
}
[[ ! -e "$tree/fs/susfs.c" && ! -e "$tree/include/linux/susfs.h" ]] || {
  echo "::error::Refusing to overwrite existing kernel SUSFS files"; exit 1;
}
# Deliberately stop on any changed context or conflict; no --reject or --3way.
git -C "$tree" apply --check --whitespace=error "$patchfile" || {
  echo "::error::Simonpunk's GKI patch does not cleanly apply to Xiaomi Rothko BSP.";
  echo "::error::Adapt the patch after reviewing actual conflicts; no unsafe overrides.";
  exit 1;
}
git -C "$tree" apply --whitespace=error "$patchfile"
cp "$susfs/kernel_patches/fs/susfs.c" "$tree/fs/susfs.c"
cp "$susfs/kernel_patches/include/linux/susfs.h" "$tree/include/linux/susfs.h"
[[ -s "$tree/fs/susfs.c" && -s "$tree/include/linux/susfs.h" ]]
if find "$tree" -name '*.rej' -o -name '*.orig' | grep -q .; then
  echo "::error::Unexpected patch reject/backup file"; exit 1;
fi
git -C "$tree" diff --check
echo "Kernel-only SUSFS patch applied; BakaSU KSU patch intentionally NOT applied."
echo "Not a device-validated kernel and NOT approved for flashing."
