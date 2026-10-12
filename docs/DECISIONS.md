# Catatan keputusan Cogan Rothko

Setiap keputusan memiliki ID. **Status** dapat berupa `Diterapkan (dokumen/CI)`,
`Disepakati (rencana)`, atau `Menunggu bukti`. Tidak ada keputusan di sini
yang merupakan perintah untuk flashing.

| ID | Tanggal | Keputusan | Status dan alasan |
|---|---|---|---|
| D-001 | 2026-10-11 | Repo source `Xiomi-14t-pro` dibuat mandiri, bukan fork. Backup fork lama tetap tersedia. | Diterapkan. Pisahkan migrasi source dengan pengembangan. |
| D-002 | 2026-10-11 | Pertahankan `bsp-rothko-u-oss` sebagai baseline; semua eksperimen di `dev/rothko`. | Diterapkan. Mencegah perubahan tidak disengaja pada dasar source. |
| D-003 | 2026-10-12 | Root manager dapat dipilih: **KSU**, **KSUN**, **BakaSU**, atau **All** (3 varian terisolasi). | Pilihan CI diterapkan; integrasi/build nyata belum. Ketiganya menggunakan jalur driver `kernelsu`, sehingga bukan instalasi gabungan. |
| D-004 | 2026-10-12 | **Tidak menggunakan DroidSpaces dan NTSync** di proyek kernel Rothko. | Diterapkan untuk opsi kerja; tidak ada kebutuhan pengguna. |
| D-005 | 2026-10-12 | Nilai `uname 6.1.170` diperlakukan sebagai **spoofed oleh SUSFS**. | Diterapkan dalam audit; jangan gunakan sebagai identitas kernel nyata. |
| D-006 | 2026-10-12 | Bedakan source Xiaomi `6.1.57`, stock firmware `6.1.138`, dan kernel GKI Cogan `6.1.177`. | Diterapkan. Perbedaan source/versi membutuhkan validasi kode, ABI dan KMI. |
| D-007 | 2026-10-12 | Simpan bukti stock **Rothko WNNIDXM**; jangan gunakan image `degas WNEIDXM` untuk flashing Rothko. | Diterapkan sebagai aturan keselamatan. |
| D-008 | 2026-10-12 | **Jangan restore `init_boot_a` atau ubah slot hanya berdasarkan dugaan**. | Diterapkan sebagai pengamanan; Slot A berfungsi, Slot B belum pasti bootable. |
| D-009 | 2026-10-12 | Audit **read-only**, validasi module vermagic/CRC dan kompatibilitas root/SUSFS/NoMount sebelum build perangkat/flash. | Masih menunggu bukti; tidak menonaktifkan `CONFIG_MODVERSIONS`. |
| D-010 | 2026-10-12 | Setiap pekerjaan terdahulu dan selanjutnya perlu dokumentasi yang dapat ditelusuri. | Diterapkan dengan indeks, log, status, dan template kontribusi. |

### D-011 — Tetap tahan flashing setelah identifikasi init_boot Degas

- **Tanggal:** 2026-10-12.
- **Bukti:** SHA-256 dari `init_boot_a` aktif cocok byte-per-byte dengan
  stock Degas WNEIDXM, bukan stock Rothko WNNIDXM.
- **Keputusan:** jangan langsung mengganti `init_boot_a` atau mengubah
  slot selama Slot A masih boot dan root berjalan; persiapkan backup
  image aktif, verifikasi source dan prosedur pemulihan sebelum tindakan.
- **Status:** aturan keselamatan sementara; flashing belum diizinkan.
- **Referensi:** [audit aktif](ROTHKO_ACTIVE_INIT_BOOT_AUDIT.md),
  [insiden](INCIDENTS.md).

### D-012 — Jaga BakaSU dan semua modul sebelum mengubah boot chain

- **Tanggal:** 2026-10-12.
- **Alasan:** backup 7 image partisi tidak mencakup modul systemless,
  konfigurasi NoMount/MetaModule, izin root, dan data modul lain pada `/data`.
- **Keputusan:** prioritas berikutnya inventaris metadata modul secara
  read-only dan rencanakan backup konfigurasi/modul yang sesuai,
  **bukan** langsung flashing atau restore `init_boot_a`.
- **Status terkini (12 Oktober 2026):** inventaris metadata telah
  berhasil dijalankan (16 modul, seluruhnya enabled-on-disk), tetapi
  **perilaku runtime dan backup konfigurasi masih menunggu bukti**.
  Daftar modul pribadi tidak dipublikasikan.
- **Referensi:** [audit modul BakaSU](ROTHKO_BAKASU_MODULE_SAFETY.md).

### D-013 — Utamakan installer ZIP untuk pemulihan modul

- **Tanggal:** 2026-10-12.
- **Permintaan pengguna:** tidak perlu backup penuh seluruh 16 modul
  jika tersedia installer ZIP dan pengguna bersedia menginstal ulang.
- **Keputusan:** gunakan strategi **installer-first**: simpan ZIP
  versi yang tepat di flashdisk dan catat versi/ketergantungan.
  Cadangkan konfigurasi khusus hanya jika sulit dibuat ulang.
- **Batasan:** berkas ZIP saja tidak memulihkan seluruh data dan
  preferensi; kernel/root BakaSU sendiri berbeda dari modul biasa.
  Belum ada audit bahwa ZIP untuk semua modul sudah tersedia.
- **Pengaman tetap:** belum ada izin restore/flash, perubahan slot
  atau eksperimen dengan `init_boot_a`.
- **Referensi:** [perlindungan modul](ROTHKO_BAKASU_MODULE_SAFETY.md).

### D-014 — Simpan kedua backup setelah pengguna mengganti init_boot

- **Tanggal:** 2026-10-12.
- **Fakta terbaru:** pengguna telah mem-flash `init_boot` stock
  Rothko lalu kernel Cogan r7 dan berhasil masuk home screen.
  Backup `09.09` tervalidasi SHA-256 7/7 dan menunjukkan
  `init_boot` berubah dari stock Degas ke **stock Rothko**;
  image lain termasuk `boot` r7 tetap sama.
- **Keputusan kerja:** jangan flash ulang untuk membuktikan
  hasil yang sudah terbukti oleh byte. Simpan backup
  `07.19` (sebelum) dan `09.09` (sesudah) secara
  **terpisah** serta buat/verifikasi salinan USB untuk
  backup terbaru tanpa menimpa versi lama.
- **Belum diketahui:** fungsi BakaSU/SUSFS/NoMount,
  16 modul dan suhu setelah reboot; boot ke home screen
  bukan validasi seluruh sistem.
- **Rujukan:** [audit pasca-flash](ROTHKO_POST_FLASH_INIT_BOOT_0909.md).
- **Status:** flash sudah dilakukan sendiri oleh pengguna;
  tindakan berikutnya hanya pembacaan/verifikasi, bukan
  instruksi flash tambahan.

## Format keputusan baru

```md
### D-XXX — Judul keputusan
- Tanggal:
- Latar belakang / masalah:
- Keputusan:
- Alternatif yang dipertimbangkan:
- Dampak / risiko:
- Status: rencana / diterapkan / dibatalkan / menunggu bukti
- Bukti: tautan commit, workflow, issue, log, atau checksum
- Koreksi atau revisi keputusan:
```

Jangan mengubah keputusan lama diam-diam. Saat keputusan dibatalkan,
catat keputusan pengganti dan alasannya dengan ID baru.

### D-015 — Form Rothko menggunakan pilihan fitur bertanda merah

- **Tanggal:** 2026-10-12.
- **Keputusan:** formulir `workflow_dispatch` untuk Rothko memuat empat
  pilihan root: KernelSU, KernelSU-Next, BakaSU (default), dan All.
  **All = tiga varian terpisah**, bukan tiga root driver dalam satu kernel.
- **Sembilan opsi fitur:** SUSFS, NoMount, Baseband Guard, Networking,
  Ptrace Patch, Unicode Fix, BPF Stack (BTF/eBPF/FUSE-BPF), Performance,
  dan *Render release notes preview only*.
- **Default:** tujuh opsi pertama aktif; Performance dan preview release
  notes tidak aktif. Semua hanya **pilihan rencana**.
- **Pengecualian:** DroidSpaces dan NTSync dihapus; jangan menyalin
  toggle tambahan ZRAM, Re-Kernel atau CVE dari workflow GKI BakaSU.
  NoMount dan BBG hanya muncul sekali, mengikuti daftar WildKernel.
- **Implementasi:** workflow pemilihan + validator kontrak + pengujian;
  **belum** mengintegrasikan root/patch, mengompilasi atau menghasilkan ZIP.
- **Alasan:** pertahankan antarmuka yang dipilih pengguna tanpa
  mencampurkan pekerjaan GKI Cogan dan BSP Rothko.
- **Status:** diterapkan pada branch PR sebagai rancangan CI, belum
  disetujui untuk flashing. Tinjau hasil GitHub Actions setelah PR dibuka.
