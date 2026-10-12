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

# Require the FULL audited GitLab commit SHA. Reject any upstream branch update.
[[ "$SUSFS_PIN" =~ ^[a-f0-9]{40}$ ]] || {
  echo "::error::SUSFS pin must be an exact 40-character lowercase SHA"; exit 1;
}
actual="$(git -C "$susfs" rev-parse HEAD)"
remote="$(git -C "$susfs" remote get-url origin)"
[[ "$remote" == "https://gitlab.com/simonpunk/susfs4ksu.git" ]] || {
  echo "::error::SUSFS source must be the official Simonpunk GitLab"; exit 1;
}
[[ "$actual" == "$SUSFS_PIN" ]] || {
  echo "::error::SUSFS SHA mismatch: expected $SUSFS_PIN, got $actual. Review upstream before repinning."; exit 1;
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
# Try original upstream patch first. For the audited Xiaomi 6.1.57 baseline
# only, prepare a deterministic context-only adaptation of five known hunks.
# Every upstream added and removed C line MUST remain identical.
# No --reject, --3way, --unidiff-zero, fuzz, or partial application.
if ! git -C "$tree" apply --check --whitespace=error "$patchfile"; then
  temp_context_patch="$(mktemp)"
  rm -f "$temp_context_patch"
  trap 'rm -f "${temp_context_patch:-}"' EXIT
  python3 "$tree/scripts/rothko_susfs_context_port.py" \
    --upstream-patch "$patchfile" --tree "$tree" \
    --output-patch "$temp_context_patch"
  patchfile="$temp_context_patch"
fi
git -C "$tree" apply --check --whitespace=error "$patchfile" || {
  python3 "$tree/scripts/rothko_susfs_hunk_matrix.py" "$tree" "$patchfile" || true
  echo "::error::Strict SUSFS patch still conflicts after context-only adaptation.";
  echo "::error::Manual semantic port required. No unsafe patch options enabled.";
  exit 1;
}
git -C "$tree" apply --whitespace=error "$patchfile"
cp "$susfs/kernel_patches/fs/susfs.c" "$tree/fs/susfs.c"
# Copy all official kernel-side SUSFS headers from the SAME pinned commit.
# Refuse missing, empty, or pre-existing destination files; never synthesize headers.
shopt -s nullglob
susfs_headers=("$susfs"/kernel_patches/include/linux/*)
(( ${#susfs_headers[@]} > 0 )) || { echo "::error::No upstream SUSFS headers"; exit 1; }
for header in "${susfs_headers[@]}"; do
  [[ -f "$header" && -s "$header" ]] || { echo "::error::Invalid SUSFS header: $header"; exit 1; }
  destination="$tree/include/linux/$(basename "$header")"
  [[ ! -e "$destination" ]] || { echo "::error::Refusing to overwrite $destination"; exit 1; }
  cp -- "$header" "$destination"
done
[[ -s "$tree/fs/susfs.c" && -s "$tree/include/linux/susfs.h" && -s "$tree/include/linux/susfs_def.h" ]] || {
  echo "::error::Required official SUSFS headers missing"; exit 1;
}
if find "$tree" -name '*.rej' -o -name '*.orig' | grep -q .; then
  echo "::error::Unexpected patch reject/backup file"; exit 1;
fi
# Detect Android page-size-migration references introduced by the patch.
# This Xiaomi BSP has no guarantee of the matching implementation. Fail closed
# rather than synthesizing VMA_PAD_START or silently changing /proc semantics.
if grep -Eq 'VMA_PAD_START[[:space:]]*\\(' "$tree/fs/proc/task_mmu.c"; then
  if ! grep -RqlE '^[[:space:]]*#[[:space:]]*define[[:space:]]+VMA_PAD_START[[:space:]]*\\(' "$tree/include" "$tree/arch/arm64/include"; then
    echo "::error::Patched task_mmu.c references VMA_PAD_START, but no matching page-size migration definition exists in kernel headers."
    echo "::error::Semantic Xiaomi BSP port required; refusing to fake a macro or modify memory-map behavior."
    exit 1
  fi
fi
git -C "$tree" diff --check
echo "Kernel-only SUSFS patch applied; BakaSU KSU patch intentionally NOT applied."
echo "Not a device-validated kernel and NOT approved for flashing."
