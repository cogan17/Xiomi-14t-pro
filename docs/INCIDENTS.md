# Insiden, ketidakpastian, dan pembelajaran

Dokumen ini menghindari kesimpulan bahwa sebuah komponen “rusak” tanpa
bukti. Tiap insiden memiliki keadaan dan kriteria penutupan.

## I-001 — Salah mengunduh ROM `degas` untuk perangkat `rothko`

- **Diketahui:** ZIP `WNEIDXM` beridentitas `degas/mt6897`, berbeda dari
  `WNNIDXM` (`rothko/mt6989`).
- **Diketahui:** `init_boot.img` kedua model memiliki isi ramdisk sangat
  mirip; ini dapat menjelaskan mengapa root manager dapat melakukan patch.
- **Snapshot pra-flash `07-19` (12 Oktober 2026):** checksum SHA-256
  `init_boot_a` yang saat itu aktif (8 MiB) **persis sama dengan stock
  Degas WNEIDXM**:
  `951f096146157773abe4cbbd9b0dacbe9c2fa6400d4c438298353e5fb8a8bf04`.
  Ini fakta tentang **kondisi sebelum** tindakan terbaru, bukan kondisi sekarang.
- **Snapshot pasca-flash `09-09` (12 Oktober 2026):** pengguna memasang
  `init_boot.img` stock Rothko WNNIDXM lalu Cogan r7, reboot masuk home,
  dan mengirim tujuh image backup. Ketujuh SHA-256 **PASS** saat dihitung
  ulang; `init_boot.img` kini **persis stock Rothko WNNIDXM**
  `4b25ce3f4a321b34aa5f84e7c8b0328065d7038c1a00b91fdcca7e0c17fe463f`.
  Keenam image lain termasuk `boot` Cogan r7 tetap identik.
  [Laporan pasca-flash](ROTHKO_POST_FLASH_INIT_BOOT_0909.md).
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
  **Addendum 12 Oktober 2026:** backup RAW Slot A terbaru
  `2026-10-12--07-19` dan salinan USB sudah diverifikasi SHA-256
  **7/7 PASS**, namun kemampuan restore belum diuji dan
  konfigurasi root/modul bukan cakupan backup tujuh image.

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

## I-005 — Riwayat bootloop modul sebelum Bootloop Protector terpasang

- **Sumber:** kesaksian langsung pengguna pada 12 Oktober 2026
  mengenai kejadian di masa lalu. Tanggal insiden, firmware/slot
  pada saat kejadian, metode flashing, dan hash image saat itu **belum diketahui**.
- **Dilaporkan:** HP mengalami bootloop yang menurut pengguna
  disebabkan modul. Pada waktu itu Bootloop Protector belum dipasang.
  Pengguna mem-flash ulang `boot.img` dan `init_boot.img`.
  Setelah tindakan tersebut HP kembali bisa boot secara normal,
  **namun seluruh modul yang sebelumnya terpasang hilang/tidak tersedia**.
- **Status bukti:** keberhasilan boot dan kehilangan modul didasarkan
  pada laporan pengguna; tidak ada log insiden, dump `/data/adb`
  sesudah flash, atau catatan versi image asal untuk membuktikan
  mekanisme kehilangan modul.
- **Pembedaan teknis:** flash hanya partisi `boot` dan `init_boot`
  biasanya tidak menimpa direktori `/data/adb/modules`. Karena itu
  tampilan modul kosong bisa menunjukkan root manager tidak mendeteksi
  modul, mounting/root berubah, modul dinonaktifkan mekanisme
  penyelamatan, atau data modul benar-benar dihapus oleh proses lain.
  **Belum dapat memilih salah satu hipotesis.**
- **Jawaban tindak lanjut pengguna (12 Oktober 2026):** pengguna
  menyatakan **tidak memperhatikan/tidak ingat sumber** `boot.img`
  dan `init_boot.img` yang dipakai saat pemulihan bootloop. Karena itu
  provenance kedua file **tidak diketahui**. Walaupun `init_boot_a`
  aktif kini identik dengan stock Degas, **tidak ada bukti** bahwa
  image Degas dipasang pada insiden tersebut atau menyebabkan
  hilangnya modul. Jangan mengisi kekosongan ini dengan dugaan.
- **Klarifikasi tambahan pengguna tentang HP sekarang:** setelah
  proses flashing ulang perangkat, pengguna membedakan instalasi
  root **LKM** (root manager mempatch `init_boot.img` dan
  image terpatch dipasang) dengan kernel root **built-in/GKI**
  seperti WildKernel dan Cogan. Insiden modul bootloop di atas
  adalah **riwayat lebih lama yang terpisah**. Tidak ada
  bukti yang menghubungkan image stock Degas `init_boot_a`
  saat ini dengan proses pemulihan bootloop lama maupun satu
  tanggal instalasi LKM tertentu.
- **Dampak pada proyek:** prioritas keselamatan sekarang mencakup
  **mempertahankan BakaSU dan modul**, bukan sekadar membuat HP
  bisa boot. Backup tujuh image RAW Slot A serta salinan USB telah
  diperiksa SHA-256 7/7 PASS; namun file installer ZIP modul dan
  pengaturan pribadi merupakan cadangan terpisah.
- **Larangan:** tidak mengulang flashing `boot/init_boot` demi
  menguji dugaan; tidak mengganti slot, disable modul, atau mengubah
  BakaSU saat perangkat sekarang berfungsi.
- **Status insiden:** pengalaman pemulihan di masa lalu tercatat;
  penyebab pasti hilangnya modul dan keterkaitan `init_boot_a`
  Degas **masih terbuka**.
- **Referensi:** [audit init_boot aktif](ROTHKO_ACTIVE_INIT_BOOT_AUDIT.md),
  [perlindungan modul](ROTHKO_BAKASU_MODULE_SAFETY.md),
  [backup Slot A/USB](ROTHKO_SLOT_A_BACKUP_INTEGRITY.md).

## Prosedur penanganan insiden baru

Catat: tanggal, perangkat, slot, firmware, perubahan terakhir, gejala,
log dan bukti (dengan data pribadi disamarkan), pemeriksaan yang
dilakukan, hasil pasti vs hipotesis, risiko, serta langkah pemulihan
yang telah **teruji**. Jangan tulis “fixed” atau “brick” tanpa dasar.
