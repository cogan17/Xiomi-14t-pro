# Status proyek — Cogan Kernel Rothko

**Snapshot:** 12 Oktober 2026 · **Bahasa:** Indonesia · **Jenis:** catatan kondisi proyek, bukan sertifikasi flash.

## Repository dan cabang

| Aspek | Keadaan yang diverifikasi |
|---|---|
| Repository pengembangan mandiri | [cogan17/Xiomi-14t-pro](https://github.com/cogan17/Xiomi-14t-pro) (`fork: false`) |
| Cabang dasar historis Xiaomi | `bsp-rothko-u-oss`, commit `924d8eb314b764a92dc7d8610def9239f0db566c` |
| Cabang kerja | `dev/rothko`; hanya perubahan pengembangan/dokumentasi di sini |
| Backup fork sumber | [cogan17/14t-pro-fork-backup](https://github.com/cogan17/14t-pro-fork-backup) |
| Versi yang tercantum dalam Makefile source | `6.1.57`; `KMI_GENERATION=11` |
| Rujukan GKI terpisah | [cogan17/GKI_BakaSU_SUSFS](https://github.com/cogan17/GKI_BakaSU_SUSFS) |

## Keadaan HP dari bukti pengguna

- Model: **Xiaomi 14T Pro**, codename `rothko`, SoC `mt6989`, Android **16**,
  firmware aktif dilaporkan `OS3.0.301.0.WNNIDXM`.
- `ro.boot.slot_suffix=_a`; Kernel Flasher menunjukkan **Slot A Active**,
  kernel image `6.1.177-android14-11-Cogan`, build
  `2026-10-10 03:36:04 UTC`, `Unbootable: No`, `Successful: Yes`.
- BakaSU driver `v4.2.0-rc3-5b76b884 (35222/5)`, manager
  `v4.2.0-rc3 (35222/5)`, SUSFS `v2.3.0`, SELinux enforcing.
- `uname` menampilkan `6.1.170` karena **spoofing SUSFS**; ini **bukan**
  sumber yang dapat dipercaya untuk menentukan versi kernel aktif.
- Modul di penyimpanan: `268` di `vendor_dlkm` dan `60` di
  `system_dlkm`; `/proc/modules` memuat `519` baris saat audit.
  `vermagic` modul contoh: `6.1.138-android14-11-...`.
- Backup **Slot B** (`backup.json` tanggal `2026-10-12--02-02`)
  memiliki `boot.img`, `init_boot.img`, `vendor_boot.img` identik
  dengan ZIP stock `WNNIDXM`; `vbmeta.img` setara di bagian image dan
  mendapat padding `0x00`; `dtbo.img` belum memiliki pembanding stock.
- Kernel Flasher menampilkan **Slot B Unbootable: Yes, Successful: No**.
  Penyebabnya **belum diketahui**; screenshot tidak membuktikan kerusakan
  partisi atau hardware.

## CI yang sudah ada (hanya audit statis)

| Pemeriksaan | GitHub Actions | Hasil sebelumnya |
|---|---|---|
| Integritas source KSU / KSUN / BakaSU | [38162499613](https://github.com/cogan17/Xiomi-14t-pro/actions/runs/38162499613) | Sukses |
| Inventaris kernel/device source | [38162743924](https://github.com/cogan17/Xiomi-14t-pro/actions/runs/38162743924) | Sukses |
| Perbedaan identitas source Xiaomi vs GKI | [38163388030](https://github.com/cogan17/Xiomi-14t-pro/actions/runs/38163388030) | Sukses |

**Perhatian:** `success` di atas hanya berarti audit statis dijalankan dengan baik.
Belum ada kernel *device-specific Rothko* hasil source BSP yang dibuat dan
disetujui untuk flashing dari proyek ini.

## Fitur yang sudah diputuskan

- Opsi root: **KernelSU**, **KernelSU-Next**, **BakaSU**, atau **All**
  (tiga varian build **terpisah**, bukan digabung pada satu kernel).
- DroidSpaces dan NTSync: **tidak dimasukkan**.
- SUSFS / NoMount: **rencana dan audit, belum disetujui untuk source BSP ini**.
- Tidak memaksa modul dengan versi tidak cocok; cek ABI/KMI dan CRC simbol.

## Blocker dan tindakan aman selanjutnya

1. Skrip [cek `init_boot_a` aktif](ROTHKO_ACTIVE_INIT_BOOT_AUDIT.md) sudah
   dibuat dan lulus validasi statis di [Actions #38168048874](https://github.com/cogan17/Xiomi-14t-pro/actions/runs/38168048874),
   tetapi **belum dijalankan pada HP**. Menentukan status LKM/degas masih
   menunggu hasil hash aktif. Backup Slot B tidak membuktikan isi Slot A.
2. Cocokkan simbol/CRC modul MediaTek yang dimuat dengan kernel GKI Cogan,
   tanpa menonaktifkan `CONFIG_MODVERSIONS`.
3. Temukan konfigurasi serta dependensi board/dtb/vendor source yang tepat
   untuk build khusus Rothko.
4. Telusuri commit `kernel/common` aktual dalam build r7, bukan hanya SHA
   commit workflow, serta hash image yang terpasang.
5. Jangan melakukan flash/restore/pergantian slot untuk menguji dugaan.

**Pengaman:** Tidak ada otorisasi flashing, reset slot, pemulihan `init_boot`
aktif, atau publikasi ZIP Rothko siap-flash berdasarkan audit ini.

Rincian dan SHA256 berada di dokumen audit terkait pada [indeks](README.md).
