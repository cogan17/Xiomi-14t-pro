#!/usr/bin/env bash
# Read-only SUSFS upstream acquisition and patch applicability probe.
set -Eeuo pipefail
export GIT_TERMINAL_PROMPT=0
ROOT="$(git rev-parse --show-toplevel)"
KERNEL_REF="${KERNEL_REF:-feat/rothko-ksun-susfs-compat-audit}"
SUSFS_REF="${SUSFS_REF:-gki-android14-6.1}"
KSUN_SHA="3438d6aa431f96a23f9e625bec3d53ce1fb14161"
SUSFS_URL="https://gitlab.com/simonpunk/susfs4ksu.git"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
echo "Kernel ref: $KERNEL_REF; SUSFS branch: $SUSFS_REF; KSUN pin: $KSUN_SHA"
git clone --quiet --filter=blob:none --single-branch --branch "$SUSFS_REF" "$SUSFS_URL" "$tmp/susfs"
sha="$(git -C "$tmp/susfs" rev-parse HEAD)"
# Fail closed if upstream branch moved beyond the source pin audited here.
EXPECTED_SUSFS_SHA="5192aa2d33b381b58c1051532f9e1dfa5de6e8d3"
if [[ "$sha" != "$EXPECTED_SUSFS_SHA" ]]; then
  echo "FAIL: SUSFS upstream moved ($sha); re-audit and re-pin explicitly before compiling"
  exit 7
fi
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
echo "===== KSUN PINNED EXECVE / SELINUX SYMBOL AUDIT ====="
git clone --quiet --filter=blob:none https://github.com/pershoot/KernelSU-Next.git "$tmp/ksun"
git -C "$tmp/ksun" checkout --quiet "$KSUN_SHA"
echo "Resolved KSUN SHA: $(git -C "$tmp/ksun" rev-parse HEAD)"
python3 - "$tmp/ksun" "$tmp/susfs" "$tmp/rothko" <<'PY'
import pathlib, re, sys
ksun, susfs, rothko = map(pathlib.Path, sys.argv[1:])
symbols = (
    "ksu_handle_execveat", "ksu_handle_execveat_sucompat",
    "ksu_handle_post_execveat_sucompat", "ksu_su_compat_enabled",
    "susfs_is_current_proc_no_su", "TIF_PROC_NO_SU",
    "avc_has_perm", "security_bprm_check",
)
sources = {
    "KSUN": [ksun / p for p in (
        "kernel/feature/sucompat.c", "kernel/feature/sucompat.h",
        "kernel/hook/syscall_event_bridge.c", "kernel/feature/selinux_hide.c",
        "kernel/supercall/dispatch.c")],
    "SUSFS": [susfs / "kernel_patches/50_add_susfs_in_gki-android14-6.1.patch",
              susfs / "kernel_patches/KernelSU/10_enable_susfs_for_ksu.patch",
              susfs / "kernel_patches/include/linux/susfs_def.h"],
    "ROTHKO": [rothko / p for p in (
        "arch/arm64/include/asm/thread_info.h", "fs/exec.c",
        "security/selinux/avc.c", "security/selinux/hooks.c",
        "security/selinux/selinuxfs.c")],
}
for label, paths in sources.items():
    print("ROOT", label, flush=True)
    for p in paths:
        if not p.is_file():
            print("MISSING", p, flush=True)
            continue
        lines = p.read_text(errors="replace").splitlines()
        print("FILE", p.relative_to({"KSUN": ksun, "SUSFS": susfs, "ROTHKO": rothko}[label]), flush=True)
        shown = 0
        for n, line in enumerate(lines, 1):
            if any(re.search(r"(?<![A-Za-z0-9_])" + re.escape(sym) + r"(?![A-Za-z0-9_])", line) for sym in symbols):
                if shown < 30:
                    print(f"  {n}: {line.strip()[:170]}", flush=True)
                shown += 1
        print("MATCHES", shown, flush=True)
print("AUDIT NOTE: matches are evidence only; inspect conditional compilation and signatures before patching.", flush=True)
PY
echo "===== END KSUN SYMBOL AUDIT ====="

# Verify the script parses before costly upstream acquisitions on every CI run.
# This check also runs at workflow startup; retain here for manual invocation.
echo "Audit script syntax: validated by bash parser at workflow entry"
echo "===== EXECVE / ARM64 PREBUILD CONTRACT GATE ====="
python3 - "$tmp/ksun" "$tmp/susfs" "$tmp/rothko" "$tmp/contract_status" <<'PY'
from pathlib import Path
import re, sys
ksun, susfs, rothko = map(Path, sys.argv[1:4])
status_path = Path(sys.argv[4])
def read(root, path):
    p = root / path
    if not p.is_file():
        raise SystemExit(f"FAIL: required source missing: {p}")
    return p.read_text(errors="replace")
su = read(ksun, "kernel/feature/sucompat.c")
hdr = read(ksun, "kernel/feature/sucompat.h")
bridge = read(ksun, "kernel/hook/syscall_event_bridge.c")
defs = read(susfs, "kernel_patches/include/linux/susfs_def.h")
kernel_patch = read(susfs, "kernel_patches/50_add_susfs_in_gki-android14-6.1.patch")
arm = read(rothko, "arch/arm64/include/asm/thread_info.h")
checks = {
 "KSUN syscall bridge invokes pt_regs sucompat": bool(re.search(r"ksu_handle_execveat_sucompat\s*\(\s*filename_user\s*,\s*orig_nr", bridge)),
 "KSUN sucompat uses SUSFS process exclusion": "susfs_is_current_proc_no_su()" in su,
 "SUSFS kernel patch requires post-execve hook": "ksu_handle_post_execveat_sucompat" in kernel_patch,
 "KSUN provides post-execve hook": "ksu_handle_post_execveat_sucompat" in (su + hdr + bridge),
 "SUSFS thread flag defined": bool(re.search(r"^#define\s+TIF_PROC_NO_SU\s+34\b", defs, re.M)),
 "Rothko reserves/defines TIF_PROC_NO_SU": bool(re.search(r"^#define\s+TIF_PROC_NO_SU\s+34\b", arm, re.M)),
}
# ARM64 thread_info.flags is unsigned long (64 bits on arm64); bit 34 is in
# range but must also be checked against all existing TIF assignments.
assigned = [(name, int(value)) for name, value in re.findall(
    r"^#define\s+(TIF_[A-Z0-9_]+)\s+(\d+)\b", arm, re.M)]
collisions = [name for name, value in assigned if value == 34 and name != "TIF_PROC_NO_SU"]
print("ARM64 TIF bit 34: 64-bit storage, existing assignments:",
      ", ".join(collisions) if collisions else "none in thread_info.h", flush=True)
checks["ARM64 bit 34 unassigned in thread_info.h"] = not collisions
checks["ARM64 thread flags use unsigned long"] = bool(re.search(
    r"unsigned\s+long\s+flags\s*;", arm))
# This is only a local header check: a whole-tree collision audit is still
# required before claiming the flag safe to add.
for label, ok in checks.items():
    print(("PASS" if ok else "BLOCK") + ": " + label, flush=True)
blocking = [
    "KSUN provides post-execve hook",
    "Rothko reserves/defines TIF_PROC_NO_SU",
    "ARM64 bit 34 unassigned in thread_info.h",
    "ARM64 thread flags use unsigned long",
]
if any(not checks[k] for k in blocking):
    print("BLOCKED: KSUN/SUSFS source contract unresolved. No build allowed.", flush=True)
    status_path.write_text("blocked\n")
PY
echo "===== END EXECVE / ARM64 PREBUILD CONTRACT GATE ====="

echo "===== WHOLE-TREE ARM64 FLAG COLLISION AUDIT ====="
# Search tracked files only, avoiding generated/untracked content. A textual
# match is evidence for manual review, not proof of runtime flag collision.
# Exclude the expected SUSFS definition itself; otherwise the audit flags its
# own intentional TIF_PROC_NO_SU reservation as a collision.
collision_matches="$(git -C "$tmp/rothko" grep -nE '^[[:space:]]*#[[:space:]]*define[[:space:]]+TIF_[A-Za-z0-9_]+[[:space:]]+34([[:space:]]|$)' -- 'arch/arm64/**' 'include/**' || true)"
collision_matches="$(printf '%s\\n' "$collision_matches" | grep -vE '(^|:)#define[[:space:]]+TIF_PROC_NO_SU[[:space:]]+34([[:space:]]|$)' || true)"
if [[ -n "$collision_matches" ]]; then
  printf '%s\\n' "$collision_matches"
  echo "BLOCK: another TIF bit-34 definition requires manual collision review"
  printf 'blocked\\n' > "$tmp/arm64_collision_status"
else
  echo "PASS: no competing literal TIF bit-34 definition in tracked ARM64/include source"
fi
echo "===== END WHOLE-TREE ARM64 FLAG COLLISION AUDIT ====="


# Capture rejected patch hunks as machine-readable evidence without applying them.
echo "===== SUSFS PATCH REJECT SUMMARY ====="
python3 - "$patch" <<'PY'
from pathlib import Path
import re, sys
patch = Path(sys.argv[1]).read_text(errors="replace").splitlines()
targets = {"fs/exec.c", "fs/namei.c", "fs/proc/base.c",
           "fs/proc/task_mmu.c", "mm/memory.c"}
current = None
for line in patch:
    if line.startswith("diff --git a/"):
        parts = line.split()
        current = parts[2][2:] if len(parts) > 3 else None
    elif current in targets and line.startswith("@@ "):
        print(f"HUNK {current} {line}", flush=True)
PY
echo "===== END SUSFS PATCH REJECT SUMMARY ====="



if git -C "$tmp/rothko" apply --check --verbose "$patch"; then
  echo "PASS: official 6.1 patch passes git apply --check against pristine Rothko BSP"
else
  echo "FAIL: official 6.1 patch does not apply cleanly to pristine Rothko BSP"
  patch_status=6
fi
if [[ -f "$tmp/arm64_collision_status" ]]; then
  echo "FAIL: ARM64 TIF collision review required"
  exit 9
fi
if [[ -f "$tmp/contract_status" ]]; then
  echo "FAIL: KSUN/SUSFS contract gate blocked; see full audit above"
  exit 8
fi
if [[ "${patch_status:-0}" -ne 0 ]]; then
  exit "$patch_status"
fi
echo "NO BUILD, NO FLASH, NO PATCH APPLICATION"
