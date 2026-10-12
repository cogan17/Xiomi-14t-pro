#!/system/bin/sh
# Cogan Rothko: private read-only root module inventory.
# Never runs module scripts or modifies files, root privileges, or slots.
set -u
export LC_ALL=C

note() { printf '%s\n' "$1"; }
prop() { getprop "$1" 2>/dev/null || true; }
if ! command -v getprop >/dev/null 2>&1; then
  note 'ERROR: getprop unavailable'
  exit 1
fi
device="$(prop ro.product.device)"
slot="$(prop ro.boot.slot_suffix)"
note '=== COGAN ROTHKO: PRIVATE BAKASU MODULE INVENTORY (READ ONLY) ==='
printf 'device=%s\nactive_slot=%s\nfirmware=%s\n' \
  "$device" "$slot" "$(prop ro.build.version.incremental)"
if [ "$device" != 'rothko' ] || [ "$slot" != '_a' ]; then
  note 'ERROR: Unexpected device/slot; stopping without scanning modules.'
  exit 1
fi
if [ "$(id -u)" != 0 ]; then
  note 'ERROR: Run with su; no permissions have been changed.'
  exit 1
fi
if command -v getenforce >/dev/null 2>&1; then
  printf 'selinux=%s\n' "$(getenforce 2>/dev/null || true)"
fi
note 'Module IDs and names may be private. Review before sharing.'

module_root='/data/adb/modules'
count=0
disabled=0
pending_remove=0
missing_props=0

module_prop() {
  # Read module.prop metadata only, NOT executable scripts/config data.
  awk -v k="$2" '
    index($0, k "=") == 1 {
      value=substr($0, length(k)+2)
      gsub(/[\r\t]/, " ", value)
      print substr(value,1,96)
      exit
    }
  ' "$1" 2>/dev/null
}
indicator() {
  if [ -e "$1" ]; then printf 'yes'; else printf 'no'; fi
}

if [ -d "$module_root" ]; then
  for path in "$module_root"/*; do
    [ -d "$path" ] || continue
    if [ -L "$path" ]; then
      note 'module_skipped_symlink=yes'
      continue
    fi
    count=$((count + 1))
    module_id="${path##*/}"
    properties="$path/module.prop"
    if [ -f "$properties" ] && [ ! -L "$properties" ]; then
      display="$(module_prop "$properties" name)"
      ver="$(module_prop "$properties" version)"
      version_code="$(module_prop "$properties" versionCode)"
    else
      display=''
      ver=''
      version_code=''
      missing_props=$((missing_props + 1))
    fi
    state='enabled_on_disk'
    if [ -e "$path/disable" ]; then
      state='disabled_on_disk'
      disabled=$((disabled + 1))
    fi
    if [ -e "$path/remove" ]; then
      pending_remove=$((pending_remove + 1))
    fi
    printf '\nmodule_id=%s\nmodule_name=%s\nmodule_version=%s\nversion_code=%s\n' \
      "$module_id" "$display" "$ver" "$version_code"
    printf 'module_disk_state=%s\nmarked_for_removal=%s\n' \
      "$state" "$(indicator "$path/remove")"
    printf 'has_service=%s\nhas_post_fs_data=%s\nhas_system_prop=%s\nhas_sepolicy_rule=%s\nhas_zygisk_dir=%s\nhas_skip_mount=%s\n' \
      "$(indicator "$path/service.sh")" \
      "$(indicator "$path/post-fs-data.sh")" \
      "$(indicator "$path/system.prop")" \
      "$(indicator "$path/sepolicy.rule")" \
      "$(indicator "$path/zygisk")" \
      "$(indicator "$path/skip_mount")"
  done
else
  note 'modules_directory=NOT_FOUND_OR_INACCESSIBLE'
fi
printf '\nmodules_count_in_directory=%s\nmodules_disabled_on_disk=%s\nmodules_marked_for_removal=%s\nmodules_without_props=%s\n' \
  "$count" "$disabled" "$pending_remove" "$missing_props"

# Only directory existence. Never display root grants, app lists or secrets.
for rel in modules_update ksu metamodule nomount service.d post-fs-data.d; do
  if [ -d "/data/adb/$rel" ]; then
    printf 'additional_directory_%s=present\n' "$rel"
  else
    printf 'additional_directory_%s=absent_or_inaccessible\n' "$rel"
  fi
done

for dir in /vendor_dlkm/lib/modules /system_dlkm/lib/modules; do
  if [ -d "$dir" ] && command -v find >/dev/null 2>&1; then
    count_ko="$(find "$dir" -maxdepth 1 -type f -name '*.ko' 2>/dev/null | wc -l | tr -d ' ')"
    printf 'kernel_module_files_%s=%s\n' "$dir" "$count_ko"
  else
    printf 'kernel_module_files_%s=unknown\n' "$dir"
  fi
done
if [ -r /proc/modules ]; then
  loaded="$(wc -l < /proc/modules 2>/dev/null || true)"
  printf 'proc_modules_lines=%s\n' "$loaded"
fi
note 'DISK STATE IS NOT PROOF OF MODULE RUNTIME FUNCTION OR ROOT PRESERVATION.'
note 'DO NOT upload this output to a public repository without review.'
note 'No file has been created or modified by this script.'
