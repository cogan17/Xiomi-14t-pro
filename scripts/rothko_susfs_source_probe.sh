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
PYecho "===== END KSUN SYMBOL AUDIT ====="

if git -C "$tmp/rothko" apply --check --verbose "$patch"; then
  echo "PASS: official 6.1 patch passes git apply --check against pristine Rothko BSP"
else
  echo "FAIL: official 6.1 patch does not apply cleanly to pristine Rothko BSP"
  exit 6
fi
echo "NO BUILD, NO FLASH, NO PATCH APPLICATION"
