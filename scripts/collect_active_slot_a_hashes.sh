#!/system/bin/sh
# Cogan Rothko: fingerprint current ACTIVE Slot A boot chain, read-only.
# Only reads block devices with sha256sum. No dd, flash, root changes or slot commands.
set -u

say() { printf '%s\n' "$1"; }
fail() { printf 'ERROR: %s\n' "$1" >&2; exit 1; }
prop() { getprop "$1" 2>/dev/null || true; }

say '=== COGAN ROTHKO: ACTIVE SLOT A BOOT CHAIN (READ ONLY) ==='
say 'This script does not back up or modify any partition.'
command -v getprop >/dev/null 2>&1 || fail 'getprop missing'
command -v blockdev >/dev/null 2>&1 || fail 'blockdev missing (needed for size safety check)'
command -v sha256sum >/dev/null 2>&1 || fail 'sha256sum missing'
command -v cut >/dev/null 2>&1 || fail 'cut missing'

device="$(prop ro.product.device)"
vendor_device="$(prop ro.product.vendor.device)"
slot="$(prop ro.boot.slot_suffix)"
firmware="$(prop ro.build.version.incremental)"
printf 'device=%s\nvendor_device=%s\nactive_slot=%s\nfirmware=%s\n' \
  "$device" "$vendor_device" "$slot" "$firmware"
[ "$device" = 'rothko' ] || fail 'Device is not rothko'
[ "$vendor_device" = 'rothko' ] || fail 'Vendor device is not rothko'
[ "$slot" = '_a' ] || fail 'Active slot is not A; refuse unexpected target'

BASE='/dev/block/by-name'
[ -d "$BASE" ] || fail 'Partition directory missing'

# These SHA-256 references came from previously examined firmware ZIPs.
ROTHKO_INIT='4b25ce3f4a321b34aa5f84e7c8b0328065d7038c1a00b91fdcca7e0c17fe463f'
DEGAS_INIT='951f096146157773abe4cbbd9b0dacbe9c2fa6400d4c438298353e5fb8a8bf04'
ROTHKO_BOOT='d8fa7c0baa2de9d6a5590c6ad2515b52fd04a32d8b2f49055a44f8864b9de4c2'
ROTHKO_VENDOR_BOOT='087e76586bb981bbd1f37334f68707bac1f3b81d9a88caa452a9433feb76a384'
# DTBO is from Slot B raw backup, not yet verified against a stock DTBO file.
SLOT_B_DTBO='47954740b3e890e0414cc5e5fc0f495c9750fe117d81f3607171d6b65c5eaff7'
# VBMETA is the 8 MiB Slot B raw backup, not the 12 KiB firmware file.
SLOT_B_VBMETA='bfe79b5ba411e927943b8b918d802dd02ed751da384d4d7752e7e6b19c32b526'

for name in boot init_boot vendor_boot dtbo vbmeta; do
  node="$BASE/$name"_a
  printf '\n--- %s ---\n' "$name"
  if [ ! -b "$node" ]; then
    printf 'status=UNAVAILABLE_OR_NOT_BLOCK_DEVICE\n'
    continue
  fi

  size="$(blockdev --getsize64 "$node" 2>/dev/null || true)"
  case "$size" in
    ''|*[!0-9]*)
      printf 'status=SIZE_NOT_AVAILABLE_SKIPPED\n'
      continue ;;
  esac
  if [ "$size" -lt 4096 ] || [ "$size" -gt 134217728 ]; then
    printf 'partition_size_bytes=%s\nstatus=UNEXPECTED_SIZE_SKIPPED\n' "$size"
    continue
  fi
  if [ "$name" = 'init_boot' ] && [ "$size" -ne 8388608 ]; then
    printf 'partition_size_bytes=%s\nstatus=UNEXPECTED_INIT_BOOT_SIZE_SKIPPED\n' "$size"
    continue
  fi
  printf 'partition_size_bytes=%s\n' "$size"
  if ! line="$(sha256sum "$node" 2>/dev/null)"; then
    printf 'status=READ_FAILED\n'
    continue
  fi
  digest="$(printf '%s\n' "$line" | cut -d ' ' -f 1)"
  printf 'sha256=%s\n' "$digest"
  case "$name:$digest" in
    "init_boot:$ROTHKO_INIT")
      say 'comparison=EXACT_STOCK_ROTHKO_INIT_BOOT' ;;
    "init_boot:$DEGAS_INIT")
      say 'comparison=EXACT_STOCK_DEGAS_INIT_BOOT' ;;
    "boot:$ROTHKO_BOOT")
      say 'comparison=EXACT_STOCK_ROTHKO_BOOT' ;;
    "vendor_boot:$ROTHKO_VENDOR_BOOT")
      say 'comparison=EXACT_STOCK_ROTHKO_VENDOR_BOOT' ;;
    "dtbo:$SLOT_B_DTBO")
      say 'comparison=MATCHES_SLOT_B_DTBO_BACKUP_NOT_PROVEN_STOCK' ;;
    "vbmeta:$SLOT_B_VBMETA")
      say 'comparison=MATCHES_SLOT_B_RAW_VBMETA_BACKUP' ;;
    *)
      say 'comparison=NO_EXACT_REFERENCE_MATCH_OR_MODIFIED' ;;
  esac
done

printf '\n%s\n' 'DONE. Read-only hashes, NOT an image backup.'
say 'No verdict on root safety, AVB compatibility or Slot B bootability.'
say 'Please share the output. DO NOT flash, restore or change slots.'
