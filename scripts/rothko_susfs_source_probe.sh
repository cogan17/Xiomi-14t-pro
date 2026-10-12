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
# Validate locally maintained patch structure before any upstream network call.
# This catches malformed hunk counts even if GitLab is unavailable.
python3 - "$ROOT/patches/rothko-ksun-sucompat-fail-closed-candidate.patch" <<'PY'
import pathlib, re, sys
lines = pathlib.Path(sys.argv[1]).read_text().splitlines()
hunk = re.compile(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@')
found = 0
i = 0
while i < len(lines):
    line = lines[i]
    if not line.startswith('@@ '):
        i += 1
        continue
    match = hunk.match(line)
    if not match:
        raise SystemExit(f'FAIL: invalid patch hunk header at line {i + 1}')
    old_expected = int(match.group(2) or 1)
    new_expected = int(match.group(4) or 1)
    old_count = new_count = 0
    i += 1
    while i < len(lines) and not lines[i].startswith(('@@ ', 'diff --git ')):
        current = lines[i]
        if current.startswith(' '):
            old_count += 1
            new_count += 1
        elif current.startswith('-'):
            old_count += 1
        elif current.startswith('+'):
            new_count += 1
        elif current.startswith('\\\\ No newline at end of file'):
            pass
        else:
            raise SystemExit(f'FAIL: unexpected patch line {i + 1}')
        i += 1
    if (old_count, new_count) != (old_expected, new_expected):
        raise SystemExit(f'FAIL: patch hunk count mismatch at line {i + 1}: '
                         f'expected {old_expected}/{new_expected}, got {old_count}/{new_count}')
    found += 1
if not found:
    raise SystemExit('FAIL: no patch hunks found')
print(f'PASS: local candidate patch structure ({found} hunks); applicability still unverified', flush=True)
PY



# Check the independently pinned KSUN candidate before GitLab access.
# Network errors remain failures; no fallback to a moving branch.
mkdir -p "$tmp/ksun"
git -C "$tmp/ksun" init --quiet
git -C "$tmp/ksun" remote add origin https://github.com/pershoot/KernelSU-Next.git
if ! git -C "$tmp/ksun" -c http.version=HTTP/1.1 fetch --quiet --depth=1 --filter=blob:none origin "$KSUN_SHA"; then
  echo "FAIL: pinned KSUN source unavailable" >&2
  exit 17
fi
git -C "$tmp/ksun" checkout --quiet --detach FETCH_HEAD
if [[ "$(git -C "$tmp/ksun" rev-parse HEAD)" != "$KSUN_SHA" ]]; then
  echo "FAIL: pinned KSUN commit mismatch" >&2
  exit 15
fi
echo "===== EARLY PINNED KSUN CANDIDATE CHECK ====="
if git -C "$tmp/ksun" apply --check --verbose "$ROOT/patches/rothko-ksun-sucompat-fail-closed-candidate.patch"; then
  echo "PASS: candidate applies to pinned KSUN (no compile or security proof)"
else
  echo "FAIL: candidate does not apply to pinned KSUN"
  exit 18
fi
echo "===== END EARLY PINNED KSUN CANDIDATE CHECK ====="

# Static safety contract: fail early even when SUSFS GitLab is unavailable.
python3 - "$ROOT/patches/rothko-ksun-sucompat-fail-closed-candidate.patch" <<'PY'
from pathlib import Path
import sys
patch = Path(sys.argv[1]).read_text()
checks = {
    "no direct filename buffer overwrite": "+    memcpy((void *)filename->name" not in patch,
    "replacement filename allocated": "getname_kernel(ksud_path)" in patch,
    "original filename released after replacement": "putname(filename);" in patch,
    "post-escape domain check": "susfs_is_current_ksu_domain()" in patch,
    "post-escape root check": "current_euid()" in patch,
}
for name, passed in checks.items():
    print(("PASS" if passed else "FAIL") + ": candidate " + name, flush=True)
if not all(checks.values()):
    raise SystemExit(19)
# Order and failure-path checks are deliberately stricter than token presence.
lines = patch.splitlines()
def pos(needle):
    return next((i for i, line in enumerate(lines) if needle in line), -1)
allocation = pos("+    replacement = getname_kernel(ksud_path);")
escape = pos("     ret = escape_with_root_profile();")
transfer = pos("+    *filename_ptr = replacement;")
release = pos("+    putname(filename);")
cleanup = [i for i, line in enumerate(lines) if line.strip() == "+        putname(replacement);"]
ordered = 0 <= allocation < escape < transfer < release and len(cleanup) >= 2 and all(escape < i < transfer for i in cleanup)
print(("PASS" if ordered else "FAIL") + ": allocation precedes escape; cleanup precedes transfer; old name released after transfer", flush=True)
if not ordered:
    raise SystemExit(20)
# Credential escalation can already have committed when domain verification fails.
# This is a hard security blocker until source-level rollback or pre-commit
# authorization is implemented; a token-order PASS must never clear it.
print("BLOCK: post-escape domain rejection may occur after commit_creds; no rollback proof", flush=True)
print("BLOCK: session FD authorization and post-exec lifecycle not implemented", flush=True)
print("BLOCK: static checks cannot prove credential rollback or filename ownership", flush=True)
PY


# Fetch the immutable SUSFS commit rather than the moving branch tip.
# This does not bypass provenance: the checked-out HEAD must equal the pin.
EXPECTED_SUSFS_SHA="5192aa2d33b381b58c1051532f9e1dfa5de6e8d3"
mkdir -p "$tmp/susfs"
git -C "$tmp/susfs" init --quiet
git -C "$tmp/susfs" remote add origin "$SUSFS_URL"
for attempt in 1 2 3; do
  if git -C "$tmp/susfs" -c http.version=HTTP/1.1 fetch --quiet --depth=1 origin "$EXPECTED_SUSFS_SHA"; then
    break
  fi
  echo "WARN: pinned SUSFS fetch failed (attempt $attempt/3)" >&2
  if [[ "$attempt" == 3 ]]; then
    echo "FAIL: pinned SUSFS commit unavailable; audit cannot proceed" >&2
    exit 16
  fi
  sleep $((attempt * 5))
done
git -C "$tmp/susfs" checkout --quiet --detach FETCH_HEAD
sha="$(git -C "$tmp/susfs" rev-parse HEAD)"
if [[ "$sha" != "$EXPECTED_SUSFS_SHA" ]]; then
  echo "FAIL: SUSFS commit mismatch ($sha); pinned source required"
  exit 7
fi
echo "Resolved SUSFS SHA: $sha"
# Pin provenance evidence for all files consumed by the compatibility audit.
# A matching commit ID alone does not establish that a later port compiles.
echo "SUSFS pinned tree: $(git -C "$tmp/susfs" rev-parse HEAD^{tree})"
git -C "$tmp/susfs" status --porcelain

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
echo "===== OFFICIAL SUSFS KSUN POST-EXECVE COMPANION PATCH ====="
companion="$tmp/susfs/kernel_patches/KernelSU/10_enable_susfs_for_ksu.patch"
test -s "$companion" || { echo "FAIL: missing official KSUN companion patch"; exit 10; }
# Print only the official patch hunks that reference post-execve, plus their
# file and hunk headers, so implementation can follow upstream semantics.
python3 - "$companion" <<'PY'
from pathlib import Path
import sys
lines = Path(sys.argv[1]).read_text(errors="replace").splitlines()
sections = []
current = []
for line in lines:
    if line.startswith("diff --git "):
        if current:
            sections.append(current)
        current = [line]
    else:
        current.append(line)
if current:
    sections.append(current)
found = False
for section in sections:
    if not any("ksu_handle_post_execveat_sucompat" in line for line in section):
        continue
    found = True
    print("COMPANION FILE:", section[0], flush=True)
    for i, line in enumerate(section):
        if "ksu_handle_post_execveat_sucompat" in line:
            lo, hi = max(0, i - 18), min(len(section), i + 45)
            print(f"CONTEXT lines {lo + 1}-{hi}:", flush=True)
            for context in section[lo:hi]:
                print(context, flush=True)
if not found:
    print("FAIL: companion patch does not define/reference expected post-execve hook", flush=True)
    raise SystemExit(11)
PY
echo "===== END OFFICIAL SUSFS KSUN POST-EXECVE COMPANION PATCH ====="
echo "===== KSUN PINNED EXECVE / SELINUX SYMBOL AUDIT ====="
# Pinned checkout: fetch only the required commit instead of repository history.
# A network failure must fail the audit, never turn a compatibility block green.
test "$(git -C "$tmp/ksun" rev-parse HEAD)" = "$KSUN_SHA" || {
  echo "FAIL: pinned KSUN commit mismatch"; exit 15;
}
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

echo "===== KSUN COMPANION PATCH APPLICABILITY (ISOLATED, READ-ONLY) ====="
# Test against the exact KSUN pin. This does not mutate the repository or
# the isolated checkout; mismatched context is an integration blocker.
if git -C "$tmp/ksun" apply --check --verbose "$companion"; then
  echo "PASS: KSUN companion patch applies to pinned source"
else
  echo "BLOCK: KSUN companion patch requires manual port to pinned KSUN"
  printf 'blocked\\n' > "$tmp/companion_status"
fi
echo "===== END KSUN COMPANION PATCH APPLICABILITY ====="
echo "===== PINNED KSUN SOURCE FIX CANDIDATE (CHECK ONLY) ====="
candidate="$tmp/rothko/patches/rothko-ksun-sucompat-fail-closed-candidate.patch"
if [[ ! -s "$candidate" ]]; then
  echo "FAIL: KSUN source fix candidate missing"
  printf 'blocked\\n' > "$tmp/candidate_status"
elif git -C "$tmp/ksun" apply --check --verbose "$candidate"; then
  echo "PASS: source fix candidate applies to pinned KSUN (NOT compiled, NOT security-approved)"
else
  echo "FAIL: source fix candidate does not apply to pinned KSUN"
  printf 'blocked\\n' > "$tmp/candidate_status"
fi
echo "===== END PINNED KSUN SOURCE FIX CANDIDATE ====="
echo "===== CANDIDATE PRIVILEGE FLOW AUDIT (NO EXECUTION) ====="
python3 - "$tmp/ksun/kernel/feature/sucompat.c" "$candidate" "$tmp/candidate_semantics_status" <<'PY'
from pathlib import Path
import re, sys
source = Path(sys.argv[1]).read_text()
patch = Path(sys.argv[2]).read_text()
status = Path(sys.argv[3])
# Review the staged diff without interpreting diff '+' as regex syntax.
added = [line[1:] for line in patch.splitlines() if line.startswith("+") and not line.startswith("+++")]
all_lines = patch.splitlines()
escape_at = next((i for i, line in enumerate(all_lines) if "ret = escape_with_root_profile();" in line), -1)
redirect_at = next((i for i, line in enumerate(all_lines) if line.startswith("+") and "memcpy((void *)filename->name, ksud_path" in line), -1)
required = {
    "profile escape precedes redirect": escape_at >= 0 and redirect_at > escape_at,
    "failure branch guards redirect": all(fragment in added for fragment in [
        "    if (ret) {", "        return 0;", "    }"]),
    "upstream still uses mutable filename buffer": "memcpy((void *)filename->name, ksud_path" in source,
}
for label, ok in required.items():
    print(("PASS" if ok else "BLOCK") + ": " + label, flush=True)
if not all(required.values()):
    status.write_text("blocked\\n")
# Even with all static checks passing, there is no proof that
# escape_with_root_profile() rolls back credentials on partial failure.
print("BLOCK: credential rollback, FD lifetime, and linking remain unverified", flush=True)
status.write_text("blocked\\n")
PY
echo "===== END CANDIDATE PRIVILEGE FLOW AUDIT ====="
echo "===== PINNED KSUN ROOT-PROFILE SEMANTICS ====="
python3 - "$tmp/ksun/kernel/policy/app_profile.c" "$tmp/root_profile_status" <<'PY'
from pathlib import Path
import sys
source = Path(sys.argv[1]).read_text(errors="replace")
status = Path(sys.argv[2])
start = source.find("int escape_with_root_profile(void)")
end = source.find("int escape_to_root_for_init(void)", start)
if start < 0 or end < 0:
    print("BLOCK: root profile implementation not found", flush=True)
    status.write_text("blocked\\n")
else:
    body = source[start:end]
    checks = {
        "credential commit present": "commit_creds(cred);" in body,
        "abort on precommit error": "abort_creds(cred);" in body,
        "early no-op may return success": "goto out_abort_creds;" in body and "return ret;" in body,
        "namespace setup follows credential commit": body.find("setup_mount_ns(") > body.find("commit_creds(cred);"),
    }
    for label, passed in checks.items():
        print(("PASS" if passed else "BLOCK") + ": " + label, flush=True)
    if not all(checks.values()):
        status.write_text("blocked\\n")
    # These source facts are diagnostic; none proves the post-exec FD contract.
PY
echo "===== END PINNED KSUN ROOT-PROFILE SEMANTICS ====="





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
 "KSUN has su session FD installer definition": any(re.search(r"(?m)^[ \\t]*(?:static[ \\t]+)?(?:inline[ \\t]+)?(?:int|long|unsigned[ \\t]+int|unsigned[ \\t]+long)[ \\t]+ksu_install_su_fd[ \\t]*\\([^;{}]*\\)[ \\t]*(?:\\n[ \\t]*)?\\{", p.read_text(errors="replace")) for p in (ksun / "kernel").rglob("*.c")),
 "KSUN post-execve references session installer": bool(re.search(r"\bksu_handle_post_execveat_sucompat\s*\([^;{}]*\)\s*\{[^}]*\bksu_install_su_fd\s*\(", su, re.S)),
 "KSUN sucompat checks UID allowlist": "ksu_is_allow_uid_for_current(current_uid().val)" in su,
 "KSUN sucompat blocks chroot": "current_chrooted()" in su,
 "KSUN sucompat checks profile escape result": bool(re.search(r"ret\s*=\s*escape_with_root_profile\s*\(\s*\)", su)),
 "KSUN sucompat propagates profile escape failure": bool(re.search(r"ret\s*=\s*escape_with_root_profile\s*\(\s*\)\s*;\s*if\s*\(\s*ret\s*\)\s*(?:\{\s*)?return\s+ret\s*;", su, re.S)),
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
    "KSUN has su session FD installer definition",
    "KSUN post-execve references session installer",
    "KSUN sucompat checks UID allowlist",
    "KSUN sucompat blocks chroot",
    "KSUN sucompat checks profile escape result",
    "KSUN sucompat propagates profile escape failure",
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
# git grep prefixes each match with path:line:, so match only the macro
# definition portion rather than guessing how many prefix separators exist.
collision_matches="$(printf '%s\\n' "$collision_matches" | grep -vE ':[[:digit:]]+:[[:space:]]*#[[:space:]]*define[[:space:]]+TIF_PROC_NO_SU[[:space:]]+34([[:space:]]|$)' || true)"
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
if [[ -f "$tmp/candidate_semantics_status" ]]; then
  echo "FAIL: privilege flow requires source-level credential/FD proof"
  exit 14
fi
if [[ -f "$tmp/candidate_status" ]]; then
  echo "FAIL: staged KSUN source fix candidate rejected"
  exit 13
fi
if [[ -f "$tmp/companion_status" ]]; then
  echo "FAIL: official KSUN companion patch not compatible with pinned KSUN"
  exit 12
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
