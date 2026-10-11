# Insiden, ketidakpastian, dan pembelajaran

Dokumen ini menghindari kesimpulan bahwa sebuah komponen “rusak” tanpa
bukti. Tiap insiden memiliki keadaan dan kriteria penutupan.

## I-001 — Salah mengunduh ROM `degas` untuk perangkat `rothko`

- **Diketahui:** ZIP `WNEIDXM` beridentitas `degas/mt6897`, berbeda dari
  `WNNIDXM` (`rothko/mt6989`).
- **Diketahui:** `init_boot.img` kedua model memiliki isi ramdisk sangat
  mirip; ini dapat menjelaskan mengapa root manager dapat melakukan patch.
- **Terverifikasi baru (12 Oktober 2026):** checksum SHA-256 image
  `init_boot_a` aktif (8 MiB) **persis sama dengan stock Degas WNEIDXM**:
  `951f096146157773abe4cbbd9b0dacbe9c2fa6400d4c438298353e5fb8a8bf04`.
  Ini bukan lagi dugaan atau sekadar image yang pernah diunduh.
- **Masih belum diketahui:** kapan/dengan proses apa image itu dipasang,
  apakah pernah menimbulkan kegagalan, dan apakah berkaitan dengan status
  Slot B unbootable. Tidak ada bukti kerusakan hardware/Slot A dari hash.
- **Tindakan:** ZIP stock Rothko yang benar sudah tersedia, tetapi jangan
  flash atau restore Slot A secara spontan. Simpan bukti image aktif,
  rencanakan backup dan langkah pemulihan sebelum perubahan.
- **Referensi:** [Audit firmware](ROTHKO_STOCK_FIRMWARE_AUDIT.md),
  [pemeriksaan `init_boot_a` aktif](ROTHKO_ACTIVE_INIT_BOOT_AUDIT.md)
  (hasil checksum dari HP sudah diperoleh).
- **Audit boot-chain tambahan:** `boot_a` berbeda dari stock Rothko,
  `vendor_boot_a` cocok dengan stock Rothko, `dtbo_a` dan `vbmeta_a`
  cocok dengan backup Slot B. [Laporan lengkap](ROTHKO_ACTIVE_SLOT_A_AUDIT.md).
  **Belum ada backup RAW Slot A terbaru yang dikonfirmasi**; risiko
  kehilangan keadaan root sekarang menjadi alasan menahan flashing.

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
