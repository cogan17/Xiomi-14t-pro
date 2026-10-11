# Insiden, ketidakpastian, dan pembelajaran

Dokumen ini menghindari kesimpulan bahwa sebuah komponen “rusak” tanpa
bukti. Tiap insiden memiliki keadaan dan kriteria penutupan.

## I-001 — Salah mengunduh ROM `degas` untuk perangkat `rothko`

- **Diketahui:** ZIP `WNEIDXM` beridentitas `degas/mt6897`, berbeda dari
  `WNNIDXM` (`rothko/mt6989`).
- **Diketahui:** `init_boot.img` kedua model memiliki isi ramdisk sangat
  mirip; ini dapat menjelaskan mengapa root manager dapat melakukan patch.
- **Belum diketahui:** apakah `init_boot_a` aktif saat ini masih memuat
  modifikasi dari ROM yang salah dan apakah pernah memicu kegagalan.
- **Tindakan:** ZIP stock Rothko yang benar sudah tersedia; **jangan**
  mengulangi flashing degas. Bandingkan image aktif secara read-only
  jika memang dibutuhkan.
- **Referensi:** [Audit firmware](ROTHKO_STOCK_FIRMWARE_AUDIT.md),
  [pemeriksaan `init_boot_a` aktif](ROTHKO_ACTIVE_INIT_BOOT_AUDIT.md)
  (skrip disiapkan, hasil pada HP belum ada).

## I-002 — Slot B bertanda `Unbootable: Yes`

- **Diketahui:** screenshot Kernel Flasher menandai Slot B
  `Unbootable: Yes`, `Successful: No`, dengan kernel stock `6.1.138`.
  Backup B diverifikasi cocok dengan firmware stock Rothko untuk
  `boot`, `init_boot`, dan `vendor_boot`.
- **Belum diketahui:** penyebab status unbootable; metadata slot yang
  tidak berhasil diakses via `bootctl`; kecocokan `dtbo`, atau seluruh
  partisi di luar lima image backup.
- **Tindakan:** jangan ganti slot, flash, atau restore untuk “membersihkan”
  indikator. Slot A aktif dan berhasil boot.
- **Referensi:** [Audit Slot B](ROTHKO_SLOT_B_BACKUP_AUDIT.md).

## I-003 — Identitas `uname` tertutup SUSFS

- **Diketahui:** perangkat melaporkan `6.1.170` melalui `uname`
  (spoofed), tetapi Kernel Flasher menunjukkan image Slot A
  `6.1.177-android14-11-Cogan`.
- **Belum diketahui:** apakah image Slot A identik byte-for-byte dengan
  artefak r7 tertentu; identitas commit `kernel/common` yang dikompilasi.
- **Tindakan:** validasi asal build dan image. Jangan matikan SUSFS
  hanya untuk melihat angka versi.
- **Referensi:** [Status](PROJECT_STATUS.md), [Lineage](ROTHKO_LINEAGE.json).

## I-004 — Riwayat kegagalan build GKI r9

- **Diketahui:** workflow Cogan GKI r9 [38127848415](https://github.com/cogan17/GKI_BakaSU_SUSFS/actions/runs/38127848415)
  gagal pada pemeriksaan sinkronisasi komponen sebelum kompilasi.
- **Belum diketahui di sini:** perbaikan upstream dan integrasi mana
  yang sudah sepenuhnya cocok dengan source Rothko.
- **Tindakan:** pertahankan validasi; jangan meloloskan build dengan
  menonaktifkan pengaman versi.
- **Referensi:** [Repo GKI](https://github.com/cogan17/GKI_BakaSU_SUSFS).

## Prosedur penanganan insiden baru

Catat: tanggal, perangkat, slot, firmware, perubahan terakhir, gejala,
log dan bukti (dengan data pribadi disamarkan), pemeriksaan yang
dilakukan, hasil pasti vs hipotesis, risiko, serta langkah pemulihan
yang telah **teruji**. Jangan tulis “fixed” atau “brick” tanpa dasar.
