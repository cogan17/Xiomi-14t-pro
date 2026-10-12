#!/system/bin/sh
# Cogan Rothko: verify RAW Kernel Flasher backup FILES (read-only).
# No block devices, no flashing, no restore, no slot change, no image upload.
set -u

folder="${1:-/sdcard/KernelFlasher/backups/2026-10-12--07-19}"
meta="$folder/backup.json"

fail() { printf 'ERROR: %s\n' "$1" >&2; exit 1; }
for cmd in awk sha256sum stat; do
  command -v "$cmd" >/dev/null 2>&1 || fail "required tool missing: $cmd"
done

[ -d "$folder" ] || fail "backup folder not found: $folder"
[ -f "$meta" ] && [ ! -L "$meta" ] || fail "regular backup.json missing: $meta"

# This parser is intentionally limited to Kernel Flasher's pretty JSON
# format, not a general-purpose JSON parser. Validate these keys explicitly.
json_value() {
  awk -F '"' -v n="$1" '$2 == n {print $4; exit}' "$meta"
}
json_hash() {
  awk -F '"' -v n="$1" '
    /"hashes"[[:space:]]*:[[:space:]]*\{/ {inside=1; next}
    inside && /^[[:space:]]*\}/ {inside=0; next}
    inside && $2 == n {print $4}
  ' "$meta"
}

backup_name="$(json_value name)"
backup_type="$(json_value type)"
hash_algorithm="$(json_value hashAlgorithm)"
case "$folder" in
  */"$backup_name") ;;
  *) fail "folder name and backup.json name do not match ($backup_name)" ;;
esac
[ "$backup_type" = raw ] || fail "expected raw backup, got: $backup_type"
[ "$hash_algorithm" = SHA-256 ] || fail "expected SHA-256 backup, got: $hash_algorithm"
[ "$backup_name" = 2026-10-12--07-19 ] || fail "this check targets 2026-10-12--07-19 only"

printf '%s\n' '=== KERNEL FLASHER RAW FILE BACKUP CHECK (READ ONLY) ==='
printf 'backup_name=%s\npath=%s\n' "$backup_name" "$folder"
printf '%s\n' 'Every image is read from the backup folder, NOT from an active partition.'

ok=0
failures=0
for name in boot init_boot vendor_boot dtbo vbmeta system_dlkm vendor_dlkm; do
  img="$folder/$name.img"
  expected="$(json_hash "$name")"
  printf '\n--- %s.img ---\n' "$name"

  case "$expected" in
    ''|*[!0123456789abcdef]*)
      printf '%s\n' 'result=MISSING_OR_INVALID_METADATA_HASH'
      failures=$((failures+1))
      continue ;;
  esac
  if [ "${#expected}" -ne 64 ]; then
    printf '%s\n' 'result=WRONG_METADATA_HASH_LENGTH'
    failures=$((failures+1))
    continue
  fi
  if [ ! -f "$img" ] || [ -L "$img" ]; then
    printf '%s\n' 'result=IMAGE_MISSING_OR_NOT_REGULAR_FILE'
    failures=$((failures+1))
    continue
  fi
  bytes="$(stat -c %s "$img" 2>/dev/null || true)"
  case "$bytes" in
    ''|*[!0123456789]*)
      printf '%s\n' 'result=UNREADABLE_FILE_SIZE'
      failures=$((failures+1))
      continue ;;
  esac
  [ "$bytes" -gt 0 ] || {
    printf '%s\n' 'result=EMPTY_IMAGE'
    failures=$((failures+1))
    continue
  }
  printf 'file_bytes=%s\nexpected_sha256=%s\n' "$bytes" "$expected"
  if ! raw="$(sha256sum "$img" 2>/dev/null)"; then
    printf '%s\n' 'result=HASH_READ_FAILED'
    failures=$((failures+1))
    continue
  fi
  actual="${raw%% *}"
  printf 'actual_sha256=%s\n' "$actual"
  if [ "$actual" = "$expected" ]; then
    printf '%s\n' 'result=PASS'
    ok=$((ok+1))
  else
    printf '%s\n' 'result=FAIL_HASH_MISMATCH'
    failures=$((failures+1))
  fi
done

printf '\nverified=%s\nfailed=%s\n' "$ok" "$failures"
if [ "$failures" -ne 0 ]; then
  printf '%s\n' 'BACKUP_FILE_VERIFICATION=FAILED (do not restore from this set)'
  exit 1
fi
printf '%s\n' 'BACKUP_FILE_VERIFICATION=PASS (file checksums match metadata)'
printf '%s\n' 'This does NOT prove that restoring is safe or that all partitions are sufficient.'
printf '%s\n' 'Keep the original backup and an independent offline copy. DO NOT flash/restore.'
