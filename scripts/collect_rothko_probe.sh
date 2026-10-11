#!/system/bin/sh
# Cogan Rothko read-only probe. Review before running with root privileges.
# No flash, no partition write, no modprobe/insmod, no SUSFS changes.
set -u
section() { printf '\n=== %s ===\n' "$1"; }
prop() {
  if command -v getprop >/dev/null 2>&1; then
    result="$(getprop "$1" 2>/dev/null || true)"
    printf '%s=%s\n' "$1" "$result"
  else
    printf '%s=<getprop unavailable>\n' "$1"
  fi
}

section 'READ-ONLY ROTHKO FIRMWARE PROBE'
printf '%s\n' 'Kernel uname may be SUSFS-spoofed: do not trust displayed release.'
section 'DEVICE / FIRMWARE'
for key in ro.product.device ro.product.vendor.device ro.build.version.release \
  ro.build.version.security_patch ro.vendor.build.version.security_patch \
  ro.build.version.incremental ro.boot.hardware ro.boot.slot_suffix; do
  prop "$key"
done
section 'CURRENT BOOT SLOT'
if command -v bootctl >/dev/null 2>&1; then
  bootctl get-current-slot 2>&1 || true
else
  printf '%s\n' 'bootctl unavailable; see ro.boot.slot_suffix above'
fi
section 'PARTITION SYMLINKS ONLY (NO RAW PARTITION READS)'
for base in /dev/block/by-name /dev/block/bootdevice/by-name /dev/block/platform/*/by-name; do
  [ -d "$base" ] || continue
  printf 'partition_directory=%s\n' "$base"
  for part in boot init_boot vendor_boot dtbo vendor_dlkm; do
    for suffix in '' _a _b; do
      p="$base/$part$suffix"
      [ -e "$p" ] || [ -L "$p" ] || continue
      ls -ld "$p" 2>/dev/null || true
    done
  done
done
section 'STATIC VENDOR MODULE METADATA'
for dir in /vendor_dlkm/lib/modules /vendor/lib/modules /odm_dlkm/lib/modules /system_dlkm/lib/modules; do
  [ -d "$dir" ] || continue
  printf 'module_directory=%s\n' "$dir"
  count="$(find "$dir" -type f -name '*.ko' 2>/dev/null | wc -l | tr -d '[:space:]')"
  printf 'regular_ko_file_count=%s\n' "$count"
  find "$dir" -type f -name '*.ko' 2>/dev/null | head -n 4 | while IFS= read -r module; do
    [ -r "$module" ] || continue
    printf 'module=%s\n' "$module"
    if command -v modinfo >/dev/null 2>&1; then
      info="$(modinfo -F vermagic "$module" 2>/dev/null || true)"
      printf 'vermagic=%s\n' "$info"
    elif command -v strings >/dev/null 2>&1; then
      info="$(strings "$module" 2>/dev/null | grep -m 1 '^vermagic=' || true)"
      printf 'vermagic_string=%s\n' "$info"
    else
      printf '%s\n' 'vermagic=unknown (no modinfo/strings tool)'
    fi
  done
done
section 'LOADED MODULE COUNT'
if [ -r /proc/modules ]; then
  wc -l < /proc/modules
else
  printf '%s\n' '/proc/modules unreadable'
fi
section 'FINAL STATUS'
printf '%s\n' 'INFORMATION ONLY: ABI compatibility not verified; do not flash/change slots.'
