# Buku kerja Cogan Rothko — append-only

Catatan ini adalah **jurnal perubahan yang sedang berlangsung**, bukan
klaim bahwa semua masalah sudah selesai. Untuk sejarah ringkas sebelum
sistem dokumentasi ada, baca [PROJECT_HISTORY.md](PROJECT_HISTORY.md).

## 2026-10-12 — Rekonstruksi pekerjaan terdahulu

- **Tujuan:** membuat satu lokasi untuk melihat migrasi source,
  pilihan KSU/KSUN/BakaSU, hasil audit GKI/Rothko, status Slot A,
  salah unduh ROM degas, dan backup Slot B.
- **Sebelumnya:** audit tersebar pada dokumen terpisah tanpa indeks
  dan kronologi lengkap.
- **Tindakan:** membuat status proyek, kronologi, keputusan,
  catatan insiden, kebijakan dokumentasi, dan indeks yang mengarah
  ke lima laporan teknis yang sudah ada.
- **Bukti:** [GitHub Actions migrasi](https://github.com/cogan17/Xiomi-14t-pro/actions/runs/38159102600),
  [audit source KSU/KSUN/BakaSU](https://github.com/cogan17/Xiomi-14t-pro/actions/runs/38162499613),
  [audit perangkat](https://github.com/cogan17/Xiomi-14t-pro/actions/runs/38162743924),
  [audit lineage](https://github.com/cogan17/Xiomi-14t-pro/actions/runs/38163388030),
  dan dokumen [Slot B](ROTHKO_SLOT_B_BACKUP_AUDIT.md).
- **Tidak dilakukan:** flashing, restore, perubahan partisi, pengubahan
  source dasar, atau menyatakan kompatibilitas ABI tuntas.
- **Belum terbukti:** penyebab Slot B unbootable, konten aktif `init_boot_a`,
  kecocokan CRC simbol modul vendor dan GKI 6.1.177.
- **Berikutnya:** audit read-only seperlunya dan perencanaan integrasi
  perangkat secara terisolasi; tetap tanpa flashing sebelum lolos gerbang.

---

Tambahkan entri baru di **akhir** dokumen dengan tanggal, bukti commit/run,
hasil yang diuji, risiko, serta batasnya. Jika menemukan kesalahan di
catatan lama, tambahkan **koreksi bertanggal** dan tautkan ke entri asal,
bukan menghapus jejak kejadian.


## 2026-10-12 — Pemeriksaan checksum image aktif

- Menambahkan skrip `scripts/check_active_init_boot.sh` untuk membaca SHA-256 dari `init_boot_a` tanpa mengubah perangkat.
- Dibandingkan dengan checksum image stock Rothko dan Degas yang telah diaudit.
- Validasi sintaks skrip di GitHub Actions berhasil: https://github.com/cogan17/Xiomi-14t-pro/actions/runs/38168048874
- Belum dijalankan pada perangkat, sehingga hasil checksum Slot A belum diketahui.
- Tidak dilakukan perubahan partisi, flashing, atau penggantian slot.
- Langkah berikutnya: pengguna meninjau skrip dan mengirim hasilnya.

## 2026-10-12 — Hasil langsung dari active init_boot_a

- **Tujuan:** melacak apakah Slot A masih menggunakan image boot ramdisk
  salah model, tanpa melakukan flashing.
- **Bukti dari HP:** `ro.product.device=rothko`, `slot=_a`,
  firmware `OS3.0.301.0.WNNIDXM`, ukuran `init_boot_a=8388608` byte.
- **Hash partisi:** `951f096146157773abe4cbbd9b0dacbe9c2fa6400d4c438298353e5fb8a8bf04`.
  Image ini **byte-identical dengan stock Degas WNEIDXM**, tidak cocok
  dengan stock Rothko; klasifikasi skrip `EXACT_DEGAS_STOCK`.
- **Konteks:** Slot A tetap aktif dan ditandai Successful; BakaSU masih
  berjalan. Backup Slot B memuat `init_boot` stock Rothko.
- **Inferensi/belum terbukti:** penyebab historis status Slot B
  Unbootable dan konsekuensi AVB/LKM belum diketahui; jangan menganggap
  hash sebagai diagnosis kerusakan hardware.
- **Tindakan repository:** audit aktif, status proyek dan catatan insiden
  diperbarui di branch `dev/rothko`.
- **Tidak dilakukan:** flashing, restore, menyalin image mentah ke repo,
  mengubah slot, modifikasi kernel/root, ataupun mematikan SUSFS.
- **Keputusan:** tahan perubahan pada slot aktif hingga tersedia backup
  aktual yang dapat diverifikasi dan rencana pemulihan yang ditinjau.
- **Rincian:** [audit init_boot_a](ROTHKO_ACTIVE_INIT_BOOT_AUDIT.md).

## 2026-10-12 — Persiapan fingerprint seluruh partisi boot Slot A

- **Tujuan:** mengenali `boot_a`, `init_boot_a`, `vendor_boot_a`, `dtbo_a`
  dan `vbmeta_a` secara read-only; menyiapkan bukti sebelum backup/pemulihan.
- **Kondisi sebelum:** `init_boot_a` terbukti identik dengan stock Degas,
  sedangkan backup Slot B berisi stock Rothko. Kernel Cogan r7 dan root
  BakaSU pada Slot A masih berjalan.
- **Tindakan:** menambahkan `scripts/collect_active_slot_a_hashes.sh`,
  dokumentasi perbandingan checksum serta CI statis.
- **Bukti:** [GitHub Actions #38168635728](https://github.com/cogan17/Xiomi-14t-pro/actions/runs/38168635728)
  selesai **success**; SHA commit awal skrip `c3d4f7d5f0b7fb1090ad3f94617bf161c40b7cc9`.
- **Hasil terverifikasi:** skrip lolos `sh -n` dan inspeksi statis.
- **BELUM diuji:** eksekusi pada HP, SHA-256 aktual lima image,
  backup Slot A terbaru, kesetaraan dengan build r7 dan ABI modul vendor.
- **Keselamatan:** tidak ada restore, flash, perubahan slot, perubahan
  root/SUSFS, ataupun pengunggahan image mentah.
- **Berikutnya:** pengguna membaca skrip dan menjalankannya dari Termux,
  kemudian mengirim hasil pemeriksaan sebelum keputusan selanjutnya.


## 2026-10-12 — Audit lengkap SHA-256 lima partisi Slot A

- **Tujuan:** mengetahui susunan boot aktual tanpa melakukan perubahan.
- **Tindakan:** pengguna menjalankan `collect_active_slot_a_hashes.sh`
  pada Xiaomi 14T Pro, firmware `OS3.0.301.0.WNNIDXM`, Slot A aktif.
- **Hasil:** `boot_a` (`67108864` B)
  `f39b666ead0c5a740a652c62225e343222b4e5fc89a560ff8f850eebf4cf6f8a`
  — berbeda dari stock Rothko.
- **Hasil:** `init_boot_a` (`8388608` B)
  `951f096146157773abe4cbbd9b0dacbe9c2fa6400d4c438298353e5fb8a8bf04`
  — identik dengan stock Degas.
- **Hasil:** `vendor_boot_a` (`67108864` B)
  `087e76586bb981bbd1f37334f68707bac1f3b81d9a88caa452a9433feb76a384`
  — identik dengan stock Rothko.
- **Hasil:** `dtbo_a` (`8388608` B)
  `47954740b3e890e0414cc5e5fc0f495c9750fe117d81f3607171d6b65c5eaff7`
  — cocok dengan backup raw Slot B, tetapi belum terbukti stock.
- **Hasil:** `vbmeta_a` (`8388608` B)
  `bfe79b5ba411e927943b8b918d802dd02ed751da384d4d7752e7e6b19c32b526`
  — cocok dengan backup raw Slot B, yang sebelumnya cocok dengan konten
  stock Rothko dengan padding nol.
- **Batas kesimpulan:** kernel image `boot_a` yang tidak stock konsisten
  dengan Kernel Flasher menunjukkan Cogan 6.1.177; belum diketahui apakah
  byte-nya identik dengan artefak r7 tertentu. Status Slot B Unbootable
  tidak dapat dijelaskan dari hash-hash ini.
- **Perubahan repo:** laporan [Tahap 8](ROTHKO_ACTIVE_SLOT_A_AUDIT.md),
  status proyek dan insiden diperbarui di `dev/rothko`.
- **Tidak dilakukan:** flashing, restore, perubahan slot, mematikan
  SUSFS, membuat backup RAW atau mengubah konfigurasi BakaSU.
- **Prioritas selanjutnya:** memastikan backup RAW Slot A terbaru
  tersedia (boot, init_boot, vendor_boot, dtbo, vbmeta) dan memeriksa
  checksum sebelum merancang opsi pemulihan.

## 2026-10-12 — Pemeriksaan metadata backup RAW Slot A

- **Input:** pengguna mengirim `backup.json` dari Kernel Flasher,
  nama backup `2026-10-12--02-40`, tipe `raw`.
- **Metadata kernel:** `6.1.177-android14-11-Cogan`, build
  `2026-10-10 03:36:04 UTC`; `bootSha1` lengkap
  `82d969f0cab5e7f17f5d499b847e7cba64a08932`.
- **Hasil yang diverifikasi:** checksum metadata untuk `boot`,
  `init_boot`, `vendor_boot`, `dtbo`, `vbmeta` seluruhnya
  **5/5 cocok** dengan hasil baca langsung Slot A melalui Termux.
- **Referensi baru:** `system_dlkm` SHA-256
  `361be1dfdf7fa5d84f4712e005d4d1925100b3e94cf04954619fd45ba18defda`;
  `vendor_dlkm` SHA-256
  `596cce7cd8e8a4a44c47080ce914facc9580004b5c18a8627c90551a3da5d536`.
- **Belum terverifikasi:** file image backup tidak dikirim bersama JSON,
  jadi ukuran/hash ulang file asli dan salinan cadangan eksternal
  **belum diperiksa**. Dua DLKM belum punya pembanding Termux.
- **Keputusan:** jangan menyimpulkan backup dapat dipulihkan hanya
  berdasarkan JSON, dan tetap tahan flashing/restoring.
- **Laporan:** [ROTHKO_ACTIVE_SLOT_A_AUDIT.md](ROTHKO_ACTIVE_SLOT_A_AUDIT.md).

## 2026-10-12 — Screenshot backup baru pukul 07.19

- **Bukti pengguna:** Kernel Flasher menampilkan `Saving backup
  2026-10-12--07-19` dan baris terakhir `Backup 2026-10-12--07-19 saved`.
- **Komponen yang ditampilkan:** `boot`, `dtbo`, `init_boot`,
  `system_dlkm`, `vbmeta`, `vendor_boot`, `vendor_dlkm`.
- **Status yang benar:** aplikasi melaporkan backup telah tersimpan.
  Ini backup **berbeda** dari `2026-10-12--02-40` dengan metadata
  sebelumnya yang 5/5 cocok dengan hash Termux.
- **Belum diperiksa:** isi folder, keberadaan `backup.json` baru,
  ketujuh file image, ukurannya, checksum file aktual, dan salinan
  penyimpanan sekunder. Log screenshot tidak secara eksplisit
  menampilkan slot target.
- **Tindak lanjut:** verifikasi file dalam folder 07.19 secara read-only,
  lalu cocokkan tiap SHA-256 dengan metadata dari folder yang sama.
- **Tidak dilakukan:** flashing, restore, perubahan root atau slot.

## 2026-10-12 — Tahap 9: verifier backup 07.19

- **Tujuan:** memverifikasi `backup.json` dan tujuh file backup raw
  pada folder `2026-10-12--07-19`, tanpa menyentuh partisi aktif.
- **Referensi kode sumber:** Kernel Flasher upstream menyimpan ke
  `/sdcard/KernelFlasher/backups/<timestamp>/<partition>.img` dan
  menulis hash SHA-256 ke `backup.json`.
- **Tindakan:** menambahkan `scripts/verify_kernel_flasher_backup.sh`,
  [petunjuk Tahap 9](ROTHKO_SLOT_A_BACKUP_INTEGRITY.md), dan
  workflow uji sintetik `test-backup-checker.yml`.
- **Uji lokal:** 7/7 file benar → pass; satu image dikorupsi → fail;
  satu image hilang → fail. GitHub Actions mengulangi skenario sintetis.
- **Belum dilakukan:** eksekusi verifier di HP, hash ulang tujuh image
  backup 07.19, validasi media penyimpanan kedua, restore, flashing.
- **Keputusan:** hanya nilai `BACKUP_FILE_VERIFICATION=PASS` setelah
  dieksekusi pada folder riil yang memvalidasi checksum file terhadap
  metadata pada folder yang sama. Ini bukan sertifikasi restore aman.

- **CI terverifikasi:** [GitHub Actions #38188533642](https://github.com/cogan17/Xiomi-14t-pro/actions/runs/38188533642) **success**: sintaks shell, semua hash benar, satu file rusak, dan satu file hilang diuji dengan data sintetik. Ini bukan hasil pemeriksaan HP.

## 2026-10-12 — Video File Manager+ backup 07.19

- **Sumber:** video layar pengguna sekitar 11 detik, bukan output verifikasi SHA.
- **Bukti visual:** folder `KernelFlasher/backups/2026-10-12--07-19`
  berisi `backup.json` (874 B) dan tepat tujuh image:
  `boot.img` (67,11 MB), `dtbo.img` (8,39 MB),
  `init_boot.img` (8,39 MB), `system_dlkm.img` (7,47 MB),
  `vbmeta.img` (8,39 MB), `vendor_boot.img` (67,11 MB),
  `vendor_dlkm.img` (21,97 MB).
- **Batas kepastian:** ukuran dibulatkan oleh file manager; checksum,
  keterbacaan penuh dan keamanan pemulihan **belum dibuktikan**.
- **Langkah lanjut:** gunakan skrip `verify_kernel_flasher_backup.sh`
  read-only pada folder 07.19 dan kirim hasilnya.
- **Tidak dilakukan:** flashing, restore, pergantian slot, modifikasi BakaSU,
  atau mengunggah image mentah ke repository.

## 2026-10-12 — Verifikasi byte 7/7 image backup 07.19

- **Input:** `backup.json` dan tujuh image mentah yang diunggah
  pengguna dari Kernel Flasher backup `2026-10-12--07-19`.
- **Metode:** baca seluruh byte image dari berkas terunggah dan hitung
  ulang SHA-256 secara independen; bandingkan dengan metadata JSON.
- **Hasil:** **7/7 PASS, 0 mismatch, 0 file hilang**.
  Total ketujuh image 188,825,600 byte (~180.08 MiB).
- **Partisi:** `boot` 67,108,864 B; `init_boot` 8,388,608 B;
  `vendor_boot` 67,108,864 B; `dtbo` 8,388,608 B;
  `vbmeta` 8,388,608 B; `system_dlkm` 7,471,104 B;
  `vendor_dlkm` 21,970,944 B.
- **Triangulasi:** lima image boot sama SHA-nya dengan pemeriksaan
  partisi aktif Termux; dua DLKM cocok dengan metadata backup.
- **Yang belum diuji:** keberadaan/verifikasi copy terpisah di media lain,
  kemampuan restore, kecocokan ABI komprehensif, dan alasan Slot B
  Unbootable. SHA cocok tidak berarti jaminan flash aman.
- **Dokumentasi:** [laporan integritas tujuh image](ROTHKO_SLOT_A_BACKUP_INTEGRITY.md).
- **Tidak dilakukan:** flashing, restore, pergantian slot, mengubah
  root/BakaSU, atau commit file image mentah ke GitHub.
- **Selanjutnya:** salin seluruh folder backup utuh beserta JSON ke
  PC/SSD/USB, verifikasi checksum kembali dan jaga Slot A tetap bekerja.

## 2026-10-12 — Tahap 10: rencana salinan independen backup Slot A

- **Bukti sebelum tahap ini:** tujuh image backup 07.19 terunggah dan seluruhnya lulus SHA-256 terhadap metadata, 7/7.
- **Tindakan:** menerbitkan prosedur salin folder tanpa menghapus asli ke Windows atau SSD, disertai perintah PowerShell yang membandingkan tujuh hash independen dengan file hasil salinan.
- **Dokumentasi:** [Tahap 10 di laporan integritas](ROTHKO_SLOT_A_BACKUP_INTEGRITY.md).
- **Belum dilakukan:** menyalin folder ke PC/SSD serta menjalankan pengecekan PowerShell pada salinan, maupun pengujian restore.
- **Keamanan:** tidak ada flashing, penulisan partisi, perubahan slot atau pengubahan BakaSU.

## 2026-10-12 — Bukti video transfer ke USB OTG

- **Sumber:** video layar MT Manager sekitar 65 detik dari pengguna.
- **Terlihat:** folder `KernelFlasher` disalin dari penyimpanan internal
  ke USB OTG, progres sekitar 180,08 MiB dan kemudian selesai.
- **Terlihat pada USB:** `KernelFlasher/backups/2026-10-12--07-19`
  berisi `backup.json` dan tujuh image, ukuran masuk akal;
  isi `backup.json` berhasil dibuka dari volume USB.
- **Pasti dari audit sebelumnya:** semua image yang diunggah ke chat
  terverifikasi 7/7 SHA-256 terhadap metadata asal.
- **Belum terverifikasi:** **SHA-256 salinan USB** belum dihitung ulang;
  video folder/JSON tidak membuktikan bytes copy identik 100%.
- **Langkah berikutnya:** jalankan verifier read-only pada path USB
  yang benar, hasil `verified=7 failed=0` menjadi gerbang penutupan.
- **Tidak dilakukan:** flashing, restore, mengganti slot, mengubah
  BakaSU, atau menerbitkan image mentah ke GitHub.

## 2026-10-12 — Verifikasi SHA-256 USB OTG final PASS 7/7

- **Bukti:** pengguna menjalankan
  `verify_kernel_flasher_backup.sh` terhadap salinan flashdisk
  di `/storage/C44C5A2F4C5A1C8C/KernelFlasher/backups/2026-10-12--07-19`.
- **Hasil langsung dari USB:** `boot`, `init_boot`,
  `vendor_boot`, `dtbo`, `vbmeta`, `system_dlkm`,
  `vendor_dlkm` masing-masing `result=PASS` setelah
  SHA-256 dihitung ulang dari image dalam folder USB.
- **Ringkasan output:** `verified=7`, `failed=0`,
  `BACKUP_FILE_VERIFICATION=PASS`.
- **Triangulasi:** tujuh file yang sebelumnya dikirim pengguna juga
  lulus 7/7 terhadap metadata asli; copy eksternal kini diverifikasi
  memiliki SHA-256 yang sama.
- **Batas pengujian:** hanya memeriksa integritas file backup, belum
  menguji fungsi pemulihan/boot, ketahanan flashdisk, ataupun
  kompatibilitas ABI/KMI/AVB dan status Slot B.
- **Keselamatan:** Slot A berjalan, kernel Cogan 6.1.177 dan BakaSU
  tidak diubah; tidak ada flashing, restore, perubahan slot atau
  pengunggahan file image ke GitHub.
- **Status tugas:** verifikasi salinan eksternal **selesai**.
- **Langkah selanjutnya:** persiapan rencana pemulihan terkontrol
  dan pemeriksaan konsekuensi root `init_boot_a` Degas, **tanpa
  menulis partisi** sampai ada keputusan setelah review.

## 2026-10-12 — Audit perlindungan BakaSU dan modul

- **Permintaan:** semua modul yang terpasang penting untuk dijaga selain
  root manager BakaSU, NoMount/MetaModule, dan driver kernel.
- **Dasar bukti:** backup partisi Slot A dan salinan USB sudah 7/7
  SHA-256 PASS; image tersebut tidak menjangkau semua data modul
  systemless dan pengaturan di `/data`.
- **Tindakan dokumentasi:** menambahkan
  [audit keselamatan modul](ROTHKO_BAKASU_MODULE_SAFETY.md),
  skrip read-only `scripts/collect_bakasu_module_inventory.sh`,
  dan workflow pemeriksaan statis terpisah.
- **Belum diuji:** inventaris modul aktual di perangkat; backup
  module installer/config dan ketergantungan NoMount/SUSFS; daftar
  izin root (disengaja tidak diekstrak untuk privasi).
- **Larangan:** tidak ada flash, restore, disable/remove modul,
  pergantian slot ataupun penulisan ke `/data/adb`.
- **Berikutnya:** jalankan skrip read-only setelah membaca isinya,
  tentukan modul kritis, lalu susun backup privat di USB dan review
  risiko sebelum mempertimbangkan perubahan `init_boot_a`.

- **Validasi skrip:** [GitHub Actions #38192045412](https://github.com/cogan17/Xiomi-14t-pro/actions/runs/38192045412) selesai **success** untuk pemeriksaan sintaks shell dan batas operasi read-only. **Belum diuji pada HP** dan belum membuktikan kompatibilitas modul.

## 2026-10-12 — Inventaris aktual enam belas modul BakaSU

- **Bukti dari HP:** skrip `collect_bakasu_module_inventory.sh` berhasil
  berjalan melalui `su`, perangkat `rothko`, Slot A, Android 16
  firmware `OS3.0.301.0.WNNIDXM`, SELinux `Enforcing`.
- **Ringkasan:** 16 modul terpasang; 16 berstatus enabled-on-disk;
  disabled=0; remove=0; seluruh modul memiliki metadata `module.prop`.
- **Jejak fitur:** 12 layanan `service.sh`, 9 `post-fs-data.sh`,
  3 `system.prop`, 4 `sepolicy.rule`, 4 `zygisk/`,
  0 `skip_mount`.
- **Data tambahan:** direktori `modules_update`, `ksu`,
  `metamodule`, `nomount`, `service.d`, `post-fs-data.d`
  ada; file `.ko` 268 di vendor, 60 di system; `/proc/modules` 519 baris.
- **Privasi:** ID, versi, dan daftar modul pribadi tidak dicatat pada
  laporan GitHub publik. Skrip tidak membaca isi konfigurasi atau
  data akses root.
- **Hasil terbatas:** enabled-on-disk bukan bukti semua 16 modul benar-benar
  berjalan; kehadiran modul Zygisk tidak otomatis berarti konflik;
  keberadaan NoMount/MetaModule perlu cek peran/runtime lebih lanjut.
- **Belum dilakukan:** backup data dan konfigurasi semua modul di
  `/data`, pemeriksaan runtime spesifik, flashing, restore,
  atau perubahan slot/daemon/fitur root.
- **Tindak lanjut:** kelompokkan ketergantungan dan buat rencana cadangan
  *private/offline* untuk modul serta konfigurasi penting. Jangan
  menyamakan backup image `boot` dan `*_dlkm` dengan backup modul.
- **Laporan:** [ROTHKO_BAKASU_MODULE_SAFETY.md](ROTHKO_BAKASU_MODULE_SAFETY.md).

## 2026-10-12 — Sederhanakan pemulihan modul berbasis ZIP

- **Preferensi pengguna:** punya installer setiap modul dan
  instal ulang jika diperlukan; tidak perlu backup penuh
  konfigurasi keenam belas modul.
- **Keputusan yang dicatat:** utamakan ZIP installer
  versi yang cocok pada flashdisk dan catat dependensinya;
  hanya simpan setelan/kunci tertentu jika sulit diulang.
- **Belum terverifikasi:** ketersediaan 16 installer ZIP
  dan checksum paket pada penyimpanan eksternal.
- **Keselamatan:** root/kernel BakaSU tetap memerlukan
  perlindungan terpisah; audit modul read-only sudah selesai;
  tidak ada flashing, restore, atau perubahan konfigurasi HP.

## 2026-10-12 — Screenshot koleksi installer modul tersusun

- **Bukti:** tiga screenshot File Manager memperlihatkan direktori
  `Penyimpanan Utama/ARoot/modulKSU/Simpan` dengan banyak subfolder
  berdasarkan kategori modul, termasuk root/systemless, Zygisk,
  MetaModule, SUSFS, dan kustomisasi perangkat.
- **Interpretasi:** arsip installer sudah **disusun oleh pengguna**;
  isi ZIP, versi installer yang tersimpan, dan kecocokan dengan
  16 modul terpasang tidak dapat dipastikan dari screenshot folder saja.
- **Catatan:** tidak terlihat folder bernama khusus ACC, YouTube Morphe,
  zygisk-detach, ataupun NoMount pada daftar yang tampil;
  keberadaan file-file itu di folder lain masih mungkin.
- **Rencana:** tidak perlu menggandakan seluruh `/data/adb` jika
  installer dan konfigurasi penting dapat disiapkan manual.
  Cadangkan koleksi installer ke USB OTG seperti backup kernel.
- **Batas bukti:** salinan dan checksum tujuh image kernel pada USB
  sudah PASS 7/7; koleksi installer yang tampak berada di
  Penyimpanan Utama **belum terbukti tersalin dan terverifikasi** di USB.
- **Tidak dilakukan:** tindakan flash, restore, hapus modul,
  ganti slot atau ubah BakaSU.

