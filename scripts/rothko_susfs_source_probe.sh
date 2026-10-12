#!/usr/bin/env bash
# Read-only SUSFS upstream acquisition and patch applicability probe.
set -Eeuo pipefail
export GIT_TERMINAL_PROMPT=0
ROOT="$(git rev-parse --show-toplevel)"
KERNEL_REF="${KERNEL_REF:-dev/rothko}"
SUSFS_REF="${SUSFS_REF:-gki-android14-6.1}"
KSUN_SHA="3438d6aa431f96a23f9e625bec3d53ce1fb14161"
SUSFS_URL="https://gitlab.com/simonpunk/susfs4ksu.git"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
echo "Kernel ref: $KERNEL_REF; SUSFS branch: $SUSFS_REF; KSUN pin: $KSUN_SHA"
git clone --quiet --filter=blob:none --single-branch --branch "$SUSFS_REF" "$SUSFS_URL" "$tmp/susfs"
sha="$(git -C "$tmp/susfs" rev-parse HEAD)"
echo "Resolved SUSFS SHA: $sha"
for f in kernel_patches/include/linux/susfs.h kernel_patches/include/linux/susfs_def.h kernel_patches/fs/susfs.c; do
  test -s "$tmp/susfs/$f" || { echo "FAIL: missing $f"; exit 2; }
  sha256sum "$tmp/susfs/$f"
done
# These requirements are for the pinned KSUN dispatcher; fail closed.
for symbol in susfs_is_current_proc_no_su TIF_PROC_NO_SU CMD_SUSFS_SHOW_VERSION CMD_SUSFS_ADD_SUS_PATH_LOOP; do
  if ! grep -Eq "\\b${symbol}\\b" "$tmp/susfs/kernel_patches/include/linux/susfs_def.h" "$tmp/susfs/kernel_patches/include/linux/susfs.h"; then
    echo "FAIL: upstream SUSFS headers missing $symbol"
    exit 3
  fi
done
# A patch may modify source files; never apply it, only git apply --check.
mapfile -t patches < <(find "$tmp/susfs/kernel_patches" -type f -name '*6.1*.patch' | sort)
if (( ${#patches[@]} == 0 )); then echo "FAIL: no 6.1 patch candidates"; exit 4; fi
echo "Kernel patch candidates (dry run only):"
printf '%s\n' "${patches[@]}"
# This probe deliberately does not guess which patch family belongs to the BSP.
echo "PENDING: select exact 6.1 BSP patch series after reviewing filenames and headers."
echo "NO BUILD, NO FLASH, NO PATCH APPLICATION"
