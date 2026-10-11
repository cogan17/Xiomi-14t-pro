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
