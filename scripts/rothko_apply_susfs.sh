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
# Read-only audit of the exact pinned upstream task_mmu.c hunks before applying.
# Expose added/removed lines and any page-size-migration references in CI.
python3 - "$patchfile" "$tree/fs/proc/task_mmu.c" <<'PY_AUDIT'
import pathlib, re, sys
patch = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
source = pathlib.Path(sys.argv[2]).read_text(encoding="utf-8")
match = re.search(r"(?m)^diff --git a/fs/proc/task_mmu\.c b/fs/proc/task_mmu\.c$", patch)
if not match:
    raise SystemExit("::error::Pinned SUSFS patch lacks task_mmu.c diff")
next_file = re.search(r"(?m)^diff --git a/", patch[match.end():])
section = patch[match.start(): match.end() + next_file.start() if next_file else len(patch)]
print("=== PINNED SUSFS task_mmu.c PATCH HUNKS (READ ONLY) ===", flush=True)
for line in section.splitlines():
    if line.startswith(("@@", "+", "-")) and not line.startswith(("+++", "---")):
        print(line, flush=True)
print("=== VMA / PAGE-SIZE DEPENDENCY REFERENCES ===", flush=True)
for label, text in (("PATCH", section), ("XIAOMI", source)):
    for n, line in enumerate(text.splitlines(), 1):
        if re.search(r"VMA_PAD_START|vma_pad_pages|VM_PAD_MASK|pgsize_migration", line):
            print(f"{label}:{n}: {line}", flush=True)
print("Audit only; no macro fallback, no semantic changes.", flush=True)
PY_AUDIT
git -C "$tree" apply --whitespace=error "$patchfile"
# Rothko semantic adaptation: Xiaomi's normal maps path reports vm_end.
# Only the pinned SUSFS OPEN_REDIRECT branch uses the unavailable Android
# page-size-migration helper. Preserve Xiaomi's identical maps boundary there.
# This is deliberately post-apply: upstream patch integrity remains checked.
python3 - "$tree/fs/proc/task_mmu.c" <<'PY_ROTHKO_VMA'
from pathlib import Path
import sys
p = Path(sys.argv[1])
s = p.read_text(encoding="utf-8")
old = "end = VMA_PAD_START(vma);"
assert s.count(old) == 1, "Unexpected VMA_PAD_START count; manual audit required"
start = s.index("#ifdef CONFIG_KSU_SUSFS_OPEN_REDIRECT", s.index("show_map_vma(struct seq_file"))
stop = s.index("#endif // #ifdef CONFIG_KSU_SUSFS_OPEN_REDIRECT", start)
assert start < s.index(old) < stop, "VMA_PAD_START outside audited OPEN_REDIRECT block"
assert "end = vma->vm_end;" in s[s.index("show_map_vma(struct seq_file"):start], "Xiaomi maps baseline changed"
s = s.replace(old, "end = vma->vm_end;", 1)
assert "VMA_PAD_START" not in s, "Unexpected remaining VMA_PAD_START"
p.write_text(s, encoding="utf-8")
print("Rothko semantic port: OPEN_REDIRECT maps end matches Xiaomi normal vm_end; single audited substitution.")
PY_ROTHKO_VMA
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
# Fail early if the patched /proc maps path references Android's
# page-size-migration helper without a definition in the kernel headers.
# This is a diagnostic guard, NOT a substitute for a semantic BSP port.
if grep -Eq 'VMA_PAD_START[[:space:]]*[(]' "$tree/fs/proc/task_mmu.c"; then
  if ! grep -RqE '^[[:space:]]*#[[:space:]]*define[[:space:]]+VMA_PAD_START([[:space:]]|[(])' "$tree/include" "$tree/arch/arm64/include"; then
    echo "::error::Patched task_mmu.c calls VMA_PAD_START but the Xiaomi BSP headers provide no definition."
    echo "::error::Semantic page-size-migration port required; refusing to synthesize a macro or alter /proc semantics."
    exit 1
  fi
fi
git -C "$tree" diff --check
echo "Kernel-only SUSFS patch applied; BakaSU KSU patch intentionally NOT applied."
echo "Not a device-validated kernel and NOT approved for flashing."
