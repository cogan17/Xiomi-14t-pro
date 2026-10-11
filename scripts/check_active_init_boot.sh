#!/system/bin/sh
# Cogan Rothko: READ-ONLY active init_boot_a SHA-256 inventory.
# Never executes flash/restore/slot changes/root installation.
set -u

ROTHKO_STOCK_SHA="4b25ce3f4a321b34aa5f84e7c8b0328065d7038c1a00b91fdcca7e0c17fe463f"
DEGAS_STOCK_SHA="951f096146157773abe4cbbd9b0dacbe9c2fa6400d4c438298353e5fb8a8bf04"
IMAGE="/dev/block/by-name/init_boot_a"

printf '%s\n' '=== COGAN ROTHKO: ACTIVE INIT_BOOT_A (READ ONLY) ==='
printf '%s\n' 'Does not flash, restore, modify root, toggle SUSFS or change boot slots.'

if ! command -v getprop >/dev/null 2>&1; then
  echo "ERROR: getprop unavailable; stopping." >&2
  exit 1
fi
device="$(getprop ro.product.device)"
slot="$(getprop ro.boot.slot_suffix)"
firmware="$(getprop ro.build.version.incremental)"
printf 'device=%s\nslot=%s\nfirmware=%s\n' "$device" "$slot" "$firmware"

if [ "$device" != "rothko" ]; then
  echo "ERROR: Device is not rothko. Nothing was read from any partition." >&2
  exit 1
fi
if [ "$slot" != "_a" ]; then
  echo "ERROR: Active slot is not A; no partition content read." >&2
  exit 1
fi
if [ ! -b "$IMAGE" ]; then
  echo "ERROR: expected block partition is missing; stopping." >&2
  exit 1
fi
if ! command -v sha256sum >/dev/null 2>&1; then
  echo "ERROR: sha256sum not available; stopping." >&2
  exit 1
fi

# The stock Rothko init_boot image is 8 MiB. Do not hash an unexpected
# partition size and accidentally compare unlike objects.
if command -v blockdev >/dev/null 2>&1; then
  size="$(blockdev --getsize64 "$IMAGE" 2>/dev/null || true)"
  if [ -n "$size" ] && [ "$size" != "8388608" ]; then
    printf 'ERROR: unexpected init_boot_a partition size: %s bytes.\n' "$size" >&2
    exit 1
  fi
  [ -n "$size" ] && printf 'partition_size_bytes=%s\n' "$size"
fi

echo "Hashing only $IMAGE (no copy or writing)..."
if ! digest_line="$(sha256sum "$IMAGE" 2>/dev/null)"; then
  echo "ERROR: unable to read/hash init_boot_a; no changes made." >&2
  exit 1
fi
digest="${digest_line%% *}"
case "$digest" in
  "$ROTHKO_STOCK_SHA")
    result="EXACT_ROTHKO_STOCK"
    detail="Byte-identical to stock Rothko WNNIDXM init_boot.img, if partition size matches." ;;
  "$DEGAS_STOCK_SHA")
    result="EXACT_DEGAS_STOCK"
    detail="Byte-identical to stock Degas WNEIDXM init_boot.img. DO NOT FLASH OR REPLACE WITHOUT REVIEW." ;;
  *)
    result="DIFFERENT_FROM_BOTH_STOCK_IMAGES"
    detail="Modified/other image. Could be root-patched; SHA-256 alone cannot identify its origin or safety." ;;
esac
printf 'init_boot_a_sha256=%s\n' "$digest"
printf 'classification=%s\n' "$result"
printf 'interpretation=%s\n' "$detail"
printf '%s\n' 'NEXT: Share this text. DO NOT restore/flash based only on the digest.'
