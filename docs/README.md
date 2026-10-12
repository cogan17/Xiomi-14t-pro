# Dokumentasi Cogan Kernel — Xiaomi 14T Pro (`rothko`)

> **Bahasa Indonesia — pusat dokumentasi kerja**  
> Repository: [Xiomi-14t-pro](https://github.com/cogan17/Xiomi-14t-pro) ·
> Cabang kerja: [dev/rothko](https://github.com/cogan17/Xiomi-14t-pro/tree/dev/rothko) ·
> Source dasar: [bsp-rothko-u-oss](https://github.com/cogan17/Xiomi-14t-pro/tree/bsp-rothko-u-oss).

**Mulai dari [STATUS PROYEK](PROJECT_STATUS.md).** Status kompatibilitas
image/ABI untuk pengembangan source BSP **belum disetujui**. Dokumen
tidak pernah menjadi izin otomatis untuk flashing.

## Navigasi utama

| Dokumen | Kegunaan |
|---|---|
| [PROJECT_STATUS.md](PROJECT_STATUS.md) | Kondisi proyek saat ini, HP, slot, root, workflow, blocker |
| [PROJECT_HISTORY.md](PROJECT_HISTORY.md) | Sejarah migrasi, build r7, firmware, insiden dan audit |
| [WORKLOG.md](WORKLOG.md) | Jurnal pekerjaan dengan tanggal/commit/uji; diperbarui tiap pekerjaan |
| [DECISIONS.md](DECISIONS.md) | Keputusan dan alasan, termasuk fitur yang disertakan/dikecualikan |
| [INCIDENTS.md](INCIDENTS.md) | Hal yang bermasalah/belum terbukti, bukti, dan tindak lanjut |
| [DOCUMENTATION_POLICY.md](DOCUMENTATION_POLICY.md) | Aturan dan format pencatatan berikutnya |

## Audit teknis dan bukti

| Dokumen | Cakupan |
|---|---|
| [ROTHKO_ROOT_SOURCE_AUDIT.md](ROTHKO_ROOT_SOURCE_AUDIT.md) | Source KSU, KSUN, BakaSU; opsi All; syarat integrasi |
| [ROTHKO_LINEAGE.json](ROTHKO_LINEAGE.json) | Identitas terstruktur Xiaomi BSP vs Google GKI |
| [ROTHKO_STOCK_FIRMWARE_AUDIT.md](ROTHKO_STOCK_FIRMWARE_AUDIT.md) | Perbandingan firmware WNNIDXM Rothko dan WNEIDXM Degas |
| [ROTHKO_VENDOR_ABI_AUDIT.md](ROTHKO_VENDOR_ABI_AUDIT.md) | KMI, metadata modul, Kernel Flasher Slot A, BakaSU/SUSFS |
| [ROTHKO_SLOT_B_BACKUP_AUDIT.md](ROTHKO_SLOT_B_BACKUP_AUDIT.md) | Checksum backup Slot B dan pembanding stock |
| [ROTHKO_ACTIVE_INIT_BOOT_AUDIT.md](ROTHKO_ACTIVE_INIT_BOOT_AUDIT.md) | Bukti checksum: `init_boot_a` aktif identik dengan stock Degas |
| [ROTHKO_ACTIVE_SLOT_A_AUDIT.md](ROTHKO_ACTIVE_SLOT_A_AUDIT.md) | Audit lanjutan boot, init_boot, vendor_boot, dtbo, vbmeta Slot A (read-only) |
| [ROTHKO_SLOT_A_BACKUP_INTEGRITY.md](ROTHKO_SLOT_A_BACKUP_INTEGRITY.md) | Verifikasi 7 file image dari backup Kernel Flasher 07.19 terhadap JSON lokal |

## Workflow pengembangan

- [Root selection preview](../.github/workflows/Patch%20Kernel%20Features.yml):
  **KSU, KSUN, BakaSU, All**; bukan build kernel.
- [Root source check](../.github/workflows/validate-root-sources.yml):
  pemeriksaan statis source yang dikunci.
- [Rothko source inventory](../.github/workflows/audit-rothko-compatibility.yml):
  audit konfigurasi/DTS/ABI GKI.
- [Kernel lineage](../.github/workflows/check-rothko-lineage.yml):
  menjaga pemisahan source Xiaomi dan GKI.
- [Read-only Termux probe](../scripts/collect_rothko_probe.sh):
  inventaris firmware dan modul.
- [Active init_boot_a checksum](../scripts/check_active_init_boot.sh):
  bandingkan image Slot A dengan stock Rothko/Degas tanpa flashing.
- [CI static safety lint](../.github/workflows/validate-init-boot-probe.yml):
  pemeriksaan skrip baru (belum membuktikan hasil pada HP).

## Audit BakaSU dan modul (sebelum pemulihan init_boot)

- [Perlindungan BakaSU, SUSFS, NoMount, dan modul](ROTHKO_BAKASU_MODULE_SAFETY.md):
  inventaris privat modul root dan file `.ko`, risiko, serta gerbang
  sebelum setiap rencana flash/restore.
- [Skrip inventaris modul read-only](../scripts/collect_bakasu_module_inventory.sh):
  membaca metadata dan flag module, tanpa membaca isi skrip/data pribadi.

## Pegangan keselamatan

**Jangan flash source atau ROM dari codename lain.** Source Xiaomi
`6.1.57`, kernel stock image `6.1.138`, dan GKI Cogan `6.1.177`
tidak dapat dipertukarkan hanya karena semua seri 6.1. Nilai `uname`
`6.1.170` diketahui sudah di-spoof SUSFS. Slot A aktif dan BakaSU
berfungsi; Slot B tercatat unbootable dengan penyebab belum jelas.
Jangan restore `init_boot_a`, mengubah slot, atau mematikan cek ABI
berdasarkan dugaan.

## Memulai pekerjaan baru

Baca **Status → Keputusan → Insiden → Worklog**; lakukan pekerjaan;
lalu simpan perubahan, bukti dan hasil pengujian sesuai
[aturan dokumentasi](DOCUMENTATION_POLICY.md).
Untuk pull request, gunakan [template](../.github/pull_request_template.md).

Source upstream `README.md` di akar repo tetap dipertahankan
apa adanya sebagai dokumen historis Android Common Kernel.
