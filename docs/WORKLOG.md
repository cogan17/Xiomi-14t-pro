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

## 2026-10-12 — Bukti ZIP di dalam subfolder modul

- **Klarifikasi pengguna:** folder-folder di
  `Penyimpanan Utama/ARoot/modulKSU/Simpan` memang menyimpan
  file installer ZIP, dikelompokkan per modul dan versi.
- **Screenshot contoh:** folder `TCP_Optimizer` memuat
  `TCP_Optimiser-2.4-16.zip` (25,45 kB) dan
  `TCP_Optimiser-2.5-17.zip` (396 kB).
- **Makna:** setidaknya satu subfolder terbukti menyimpan ZIP;
  pengguna menyatakan pola ini berlaku untuk koleksi arsipnya.
  Belum ada validasi isi/versi tiap ZIP atau kecocokan dengan
  seluruh 16 modul terpasang.
- **Pemisahan:** arsip ZIP tersimpan tidak berarti modul terinstal
  atau aktif. Tidak ada rencana mengaktifkan TCP Optimizer.
- **Keselamatan:** flashdisk backup 7 image Cogan tetap
  PASS 7/7; belum mengklaim koleksi installer juga sudah
  diverifikasi di USB. Tidak dilakukan flashing atau perubahan root.

## 2026-10-12 — Konfirmasi fokus referensi stock Rothko

- **Bukti:** screenshot pengguna memperlihatkan folder
  `Penyimpanan Utama/OS3.0.301.0.WNNIDXM` dengan
  `boot.img`, `init_boot.img`, `vendor_boot.img`,
  `vbmeta.img`, `vbmeta_system.img`, `vbmeta_vendor.img`,
  `preloader_raw.img`, teks metadata, dan ZIP WNNIDXM.
- **Arahan utama:** file stock adalah bahan pembanding rantai boot
  `rothko`, khususnya untuk analisis `init_boot_a` aktif
  yang identik dengan stock `degas`, sementara `boot_a`
  adalah Cogan r7 yang saat ini berhasil boot.
- **Perhatian:** jangan mengasumsikan gambar folder berarti
  checksum file yang disimpan sekarang telah diperiksa;
  zip yang diaudit sebelumnya berbeda bukti dari screenshot.
- **Batas keselamatan:** tidak menyentuh `preloader_raw`,
  tidak flashing/restore/ganti slot/ubah BakaSU atau modul;
  tetap menuntut analisis AVB, kompatibilitas kernel/root,
  dan rencana pemulihan sebelum keputusan apa pun.
- **Referensi:** [audit firmware stock](ROTHKO_STOCK_FIRMWARE_AUDIT.md),
  [audit init_boot aktif](ROTHKO_ACTIVE_INIT_BOOT_AUDIT.md).

## 2026-10-12 — Riwayat bootloop modul dan kehilangan modul setelah flashing

- **Dilaporkan pengguna:** pada insiden lampau HP bootloop karena modul,
  sebelum Bootloop Protector dipasang. Pengguna mem-flash
  `boot.img` dan `init_boot.img`; HP berhasil boot kembali, tetapi
  semua modul yang pernah terpasang hilang/tidak tersedia.
- **Belum diketahui:** apakah modul benar-benar terhapus dari
  `/data/adb/modules` atau tidak lagi terlihat/aktif di root manager;
  waktu dan tool flashing, slot target, serta sumber image yang dipakai.
- **Relevansi kuat untuk diselidiki, bukan kesimpulan:** saat ini
  `init_boot_a` aktif cocok stock Degas WNEIDXM, berbeda dari stock
  Rothko WNNIDXM. Belum terbukti apakah image tersebut berasal dari
  insiden bootloop yang diceritakan.
- **Dampak:** rumus aman proyek bukan hanya 'bisa boot', tetapi
  'BakaSU dan semua modul penting dapat dipulihkan bila perlu'.
  Instalasi ulang ZIP merupakan pilihan pengguna; integritas
  backup 7 image kernel/USB telah terverifikasi sebelumnya.
- **Tindakan:** insiden I-005 dicatat, tetap read-only.
  Tidak melakukan flashing, restore, reset slot atau modifikasi modul.

## 2026-10-12 — Klarifikasi LKM init_boot vs GKI built-in

- **Keterangan pengguna:** kejadian bootloop lama terpisah dari
  kondisi HP saat ini yang sudah melalui flashing ulang.
  Pada instalasi root metode LKM, root manager biasanya mempatch
  `init_boot.img`, hasil patch di-flash dan Manager lalu
  menandai mode LKM.
- **Mode berbeda:** pemasangan kernel patch seperti WildKernel
  atau Cogan menyediakan root built-in/GKI melalui kernel custom.
  Tidak sama dengan hanya mempatch `init_boot.img`.
- **Referensi:** panduan instalasi KernelSU
  https://kernelsu.org/id_ID/guide/installation.html
  dan upstream BakaSU https://github.com/Baka-SU/BakaSU.
- **Kesenjangan bukti:** belum ada urutan lengkap setiap image
  terpatch/stock yang dipasang setelah reflashing; tidak boleh
  menyimpulkan cara image Degas identik stock bisa berada pada
  `init_boot_a` sekarang hanya dari penjelasan metode.
- **Status aman:** tetap root Cogan BakaSU aktif, backup Slot A/USB
  7/7 PASS, tidak mengubah partisi atau modul.

## 2026-10-12 — Laporan operasional init_boot Degas dan suhu fluktuatif

- **Kesaksian pengguna:** tidak merasa ada gangguan sistem lain
  selama memakai HP dengan `init_boot_a` yang teridentifikasi
  identik stock Degas; pengecualian adalah suhu perangkat yang
  naik-turun. Pernah dilaporkan suhu baterai 39–40°C pada
  evaluasi kernel Cogan r7.
- **Pembedaan fakta:** `init_boot_a` hash identik stock Degas;
  riwayat lama patch LKM tidak membuktikan image saat ini
  masih berisi patch. Fungsi HP/16 modul saat ini tidak
  membuktikan semua path boot/OTA akan aman.
- **Keputusan:** status suhu merupakan pertanyaan diagnostik
  **terpisah**; faktor beban perangkat, kebijakan thermal
  dan konfigurasi modul harus diperiksa sebelum korelasi sebab.
  Tidak ada alasan yang cukup untuk mengganti image hanya
  demi mencoba menyembuhkan suhu.
- **Pengaman:** Slot A tetap digunakan, tidak flashing,
  restore, reboot eksperimen atau perubahan kernel/modul.
- **Rujukan:** [audit init_boot aktif](ROTHKO_ACTIVE_INIT_BOOT_AUDIT.md).

## 2026-10-12 — Pengguna menjalankan metode fatalcoder: init Rothko lalu Cogan r7

- **Tindakan yang dilaporkan pengguna:** flash `init_boot.img` Rothko lalu
  installer Cogan r7, reboot berhasil mencapai home screen, kemudian
  membuat backup RAW `2026-10-12--09-09`.
- **Bukti:** log Kernel Flasher/AnyKernel3 pukul 09.07, manifest
  backup `09-09` dan ketujuh image RAW yang diunggah.
- **Audit independen:** semua tujuh SHA-256 image cocok manifest.
  **Enam image identik dibanding `07-19`**, termasuk `boot` Cogan r7.
  Satu-satunya perubahan adalah `init_boot.img`: SHA-256 `951f0961...`
  (stock Degas) → `4b25ce3f...` (stock Rothko).
- **Log installer:** menargetkan `/dev/block/by-name/boot_a`, GKI
  supported, header boot v4, repack/penulisan boot, selesai `Done!`.
  `ash: bad number` dicatat sebagai warning yang tidak menghentikan
  log instalasi, penyebabnya belum dianalisis.
- **Batas bukti:** pengguna melaporkan reboot berhasil; belum ada uji
  root Manager/Driver, SUSFS, NoMount dan seluruh 16 modul pasca-flash.
  Backup baru `09-09` belum terverifikasi pada USB, sementara copy USB
  `07-19` sudah PASS 7/7. Pertahankan **kedua** kondisi.
- **Tidak dilakukan oleh asisten:** flashing, reboot, penulisan
  partisi, perubahan slot/root/modul, atau publikasi image mentah.
- **Referensi:** [laporan lengkap](ROTHKO_POST_FLASH_INIT_BOOT_0909.md).

## 2026-10-12 — Penyesuaian fitur Rothko mengikuti screenshot bertanda merah

- **Tujuan:** menyiapkan formulir Rothko seperti contoh WildKernel tanpa
  menyalin toggle tambahan dari proyek GKI BakaSU.
- **Sebelumnya:** root pilihan KSU/KSUN/BakaSU/All sudah tersedia, tetapi
  beberapa fitur bukan dari screenshot dan default BBG/networking/BPF
  tidak konsisten dengan pilihan pengguna.
- **Tindakan:** branch `feat/rothko-root-feature-form-20261012`, ubah
  `.github/workflows/Patch Kernel Features.yml` menjadi tepat 10 input
  (satu root, sembilan opsi fitur). Tambahkan validator
  `scripts/rothko_feature_plan.py` dan pengujian kontrak.
- **Yang dipertahankan:** BakaSU default; KSU/KSUN/BakaSU/All; All
  menghasilkan tiga matriks root terpisah, bukan root gabungan.
- **Yang dihapus dari form Rothko:** DroidSpaces, NTSync, toggle
  GKI-only ZRAM, Re-Kernel, dan CVE; tidak ada duplikasi NoMount/BBG.
- **Validasi:** unit test dan workflow PR disiapkan; hasil Actions
  akan dicatat setelah run, bukan diklaim sukses sebelum ada hasil.
- **Source/firmware/perangkat:** tidak diubah; tidak ada flashing,
  pergantian slot, kompilasi, ZIP, Manager APK, atau patch penerapan nyata.
- **Status:** pekerjaan pada branch PR menuju `dev/rothko`, menunggu
  pemeriksaan CI dan review; baseline `bsp-rothko-u-oss` tetap utuh.
- **Langkah berikut:** uji PR, tinjau matriks/summary, lalu lakukan audit
  ABI/KMI/board/pinning patch sebelum membuat jalur build sesungguhnya.

## 2026-10-12 — Implementasi dua jalur distribusi (kandidat, belum flash)

- Kode: `scripts/rothko_dual_package.py` membuat pasangan `boot.img`
  dan AnyKernel3 ZIP dari `Image` yang sama, memverifikasi kernel
  tersemat pada `boot.img` dan mencatat hash SHA-256.
- Windows: `tools/platform-tools/flash-rothko.cmd` dan
  `Flash-Rothko.ps1` menyiapkan pemeriksaan Platform-Tools,
  khusus `rothko`/Slot A/partisi boot; default read-only.
- **Keamanan:** output diberi `approved_for_flash=false`; AK3
  mengandung blokir eksekusi. Tidak ada ZIP siap-flash, kompilasi,
  perubahan partisi, atau flashing perangkat.
- Uji kontrak dengan data sintetik ditambahkan ke CI. Tidak
  membuktikan kecocokan ABI/KMI atau kemampuan boot di Rothko.
- Berikutnya: temukan konfigurasi board/DT yang benar, kompile
  kernel khusus perangkat, cocokkan vendor ABI serta firmware
  sebelum meninjau izin instalasi dua format.

## 2026-10-12 — Tahap kompilasi BSP ARM64 (diagnostik)

- Menambahkan workflow `rothko-bsp-compile-smoke.yml` dan skrip
  `rothko_bsp_compile_smoke.sh` untuk benar-benar menjalankan compiler
  pada source Xiaomi 6.1.57 menggunakan `gki_defconfig`.
- Validasi provenance 6.1.57/KMI 11 dan keberadaan branch
  `MiCode/MTK_kernel_modules:bsp-rothko-u-oss`.
- Batasan: generic `gki_defconfig` **belum** board config Rothko;
  host clang **belum** toolchain produksi terpin; modul vendor, root,
  SUSFS dan NoMount belum diintegrasikan.
- Tidak mengunggah kernel Image, APK, ZIP AK3, boot.img, atau rilis;
  tidak mengubah partisi HP/slot. Hasil CI akan dinilai dari GitHub.
- Langkah berikut: gunakan hasil kompilasi untuk menindaklanjuti
  toolchain/konfigurasi board + modul vendor, bukan menandai flash-ready.

## 2026-10-12 — Integrasi driver KSU/KSUN/BakaSU pada source BSP (eksperimental)

- Skrip `rothko_install_root_driver.py` memasang tepat satu driver
  root pada checkout kernel sementara dengan SHA upstream yang dipin.
  Tidak menjalankan `setup.sh` upstream, menolak integrasi duplikat,
  dan mempertahankan versi source Xiaomi 6.1.57 serta KMI 11.
- Workflow menguji ketiga varian di workspace masing-masing dan
  mencoba kompilasi diagnostik `Image` BakaSU dengan root aktif.
- SUSFS, NoMount dan patch fitur lain **belum** diterapkan;
  konfigurasi GKI generik belum dinyatakan cocok perangkat Rothko.
- Tidak ada image APK/AK3/boot.img yang dipublikasikan atau di-flash.
- Keberhasilan atau kegagalan kompilasi ditentukan oleh hasil CI PR.

## 2026-10-12 — NoMount native integration (eksperimental)

- Menambahkan `rothko_install_nomount.py`: integrasi sumber resmi
  NoMount `maxsteeel/nomount` SHA `8005194827ca3edc7e75b9523a874307b2c3e883`
  ke `fs/nomount` pada checkout CI terisolasi, tanpa menjalankan setup
  script jaringan dan tanpa menduplikasi Kconfig/Makefile.
- CI mencoba kompilasi `CONFIG_NOMOUNT=y` dengan `CONFIG_MODVERSIONS=y`
  dan source BSP 6.1.57 generik; hasilnya dilihat dari run PR.
- **Belum** diuji bersama driver KSU/KSUN/BakaSU, SUSFS, MetaModule,
  konfigurasi board Rothko/MT6989, maupun modul vendor.
- Tidak ada boot.img, AK3, release, artifact siap-flash, atau tindakan HP.

## 2026-10-12 — Uji kompilasi gabungan BakaSU + NoMount

- Workflow `rothko-bakasu-nomount-combined.yml` menjalankan integrasi
  source BakaSU dan NoMount dari SHA terpin dalam **checkout yang sama**,
  dengan `CONFIG_KSU=y`, `CONFIG_NOMOUNT=y`, `CONFIG_MODVERSIONS=y`.
- Kompilasi menggunakan generic GKI defconfig di source BSP 6.1.57;
  SUSFS sengaja belum dinyalakan sampai patch kernel tervalidasi.
- Tidak ada output siap-flash, release, perintah fastboot, atau perubahan HP.
- Status kompilasi final harus diambil dari GitHub Actions PR; tidak
  membuktikan ABI/KMI/modul/DT vendor khusus Rothko.

## 2026-10-14 — Root source pin audit: upstream drift warning (PR #13)

- **Tujuan:** mencegah kegagalan palsu audit sumber KSUN/BakaSU ketika HEAD branch upstream bergerak, tanpa mengubah versi sumber yang diaudit.
- **Perubahan:** `.github/workflows/validate-root-sources.yml` tetap memakai SHA terpin untuk pengunduhan dan pemeriksaan statis. Pemeriksaan keberadaan commit terpin memakai GitHub commit API; perbedaan HEAD upstream hanya menghasilkan warning dan ringkasan, tidak melakukan pembaruan pin otomatis.
- **Pengaman:** SHA harus berbentuk 40 digit heksadesimal, commit terpin harus tersedia, dan pemeriksaan `setup.sh`, `Kconfig`, `Makefile` tetap fail-closed. Tidak ada eksekusi setup, integrasi kernel, maupun perubahan KSU/Mama.
- **Bukti:** PR #13 https://github.com/cogan17/Xiomi-14t-pro/pull/13 ; commit awal `b1fdb31508eebd28144c501e5ad36cb395085fc5`.
- **Batas:** hasil kedua matrix audit dan Documentation Guard harus diverifikasi setelah commit ini; perubahan upstream belum dinilai kompatibel, dan tidak ada izin build/merge kernel atau flashing.
