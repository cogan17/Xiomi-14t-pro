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
echo "Upstream SUSFS patch inventory:"
find "$tmp/susfs/kernel_patches" -type f -name "*.patch" | sort | head -100
for f in kernel_patches/include/linux/susfs.h kernel_patches/include/linux/susfs_def.h kernel_patches/fs/susfs.c; do
  test -s "$tmp/susfs/$f" || { echo "FAIL: missing $f"; exit 2; }
  sha256sum "$tmp/susfs/$f"
done
# These requirements are for the pinned KSUN dispatcher; fail closed.
for symbol in susfs_is_current_proc_no_su TIF_PROC_NO_SU CMD_SUSFS_SHOW_VERSION CMD_SUSFS_ADD_SUS_PATH_LOOP; do
  if ! grep -Eq "(^|[^[:alnum:]_])${symbol}([^[:alnum:]_]|$)" "$tmp/susfs/kernel_patches/include/linux/susfs_def.h" "$tmp/susfs/kernel_patches/include/linux/susfs.h"; then
    echo "FAIL: upstream SUSFS headers missing $symbol"
    exit 3
  fi
done
# A patch may modify source files; never apply it, only git apply --check.
mapfile -t patches < <(find "$tmp/susfs/kernel_patches" -type f -name '*6.1*.patch' | sort)
if (( ${#patches[@]} == 0 )); then echo "FAIL: no 6.1 patch candidates"; exit 4; fi
echo "Kernel patch candidates (dry run only):"
printf '%s\n' "${patches[@]}"
# Apply-check only against a fresh isolated checkout of the pinned Rothko BSP.
# No git apply is performed. This is a diagnostic patch-context test.
patch="$tmp/susfs/kernel_patches/50_add_susfs_in_gki-android14-6.1.patch"
test -s "$patch" || { echo "FAIL: expected Android 14 / 6.1 patch absent"; exit 5; }
git clone --quiet --filter=blob:none --single-branch --branch "$KERNEL_REF" "https://github.com/cogan17/Xiomi-14t-pro.git" "$tmp/rothko"
echo "Rothko source SHA: $(git -C "$tmp/rothko" rev-parse HEAD)"
# Evidence-only report of the exact upstream diff; do not apply it.
# Limit console output to the five rejected files; preserve full upstream
# context, added and removed lines in the workflow log for human review.
echo "===== PINNED SUSFS DIFF: FIVE REJECTED FILES ====="
python3 - "$patch" <<'PY'
import pathlib, sys
patch = pathlib.Path(sys.argv[1]).read_text(errors="replace").splitlines()
targets = {"fs/exec.c", "fs/namei.c", "fs/proc/base.c",
           "fs/proc/task_mmu.c", "mm/memory.c"}
active = False
for line in patch:
    if line.startswith("diff --git a/"):
        fields = line.split()
        active = len(fields) >= 4 and fields[2][2:] in targets
    if active:
        print(line)
PY
echo "===== END PINNED SUSFS DIFF ====="
if git -C "$tmp/rothko" apply --check --verbose "$patch"; then
  echo "PASS: official 6.1 patch passes git apply --check against pristine Rothko BSP"
else
  echo "FAIL: official 6.1 patch does not apply cleanly to pristine Rothko BSP"
  exit 6
fi
echo "NO BUILD, NO FLASH, NO PATCH APPLICATION"
