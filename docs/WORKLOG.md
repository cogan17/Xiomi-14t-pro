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
