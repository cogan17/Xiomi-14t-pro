# Tahap 9 — Verifikasi integritas backup RAW Kernel Flasher

**Tanggal persiapan:** 12 Oktober 2026  
**Status:** skrip diuji dengan tujuh file sintetik secara lokal; **belum dijalankan pada backup HP pengguna**. Semua operasi membaca **file yang sudah disimpan**, bukan partisi.

## Dua backup yang tidak boleh tertukar

| Nama folder | Bukti | Status |
|---|---|---|
| `2026-10-12--02-40` | `backup.json` telah dikirim; hash untuk 5 partisi boot identik dengan SHA-256 pembacaan aktif Slot A via Termux. | Kebenaran keberadaan dan integritas 7 file image belum diperiksa. |
| `2026-10-12--07-19` | Screenshot Kernel Flasher menunjukkan `Backup 2026-10-12--07-19 saved`, dengan `boot`, `dtbo`, `init_boot`, `system_dlkm`, `vbmeta`, `vendor_boot`, `vendor_dlkm`. | **Belum ada file `backup.json` dari backup 07.19 atau SHA-256 tujuh file yang dihitung ulang**. |

### Lokasi yang ditemukan dari kode sumber aplikasi

Pada [Kernel Flasher upstream](https://github.com/capntrips/KernelFlasher/blob/main/app/src/main/java/com/github/capntrips/kernelflasher/ui/screens/slot/SlotViewModel.kt),
fungsi `createBackupDir` menyimpan backup di `/sdcard/KernelFlasher/backups/<nama>`.
Fungsi `backupPartitions` menulis file sebagai `<partition>.img`, mencatat SHA-256
pada `backup.json`. Lokasi ini **belum dikonfirmasi di perangkat**,
khususnya bila memakai fork/versi modifikasi.

## Verifier read-only untuk backup 07.19

[Skrip `scripts/verify_kernel_flasher_backup.sh`](../scripts/verify_kernel_flasher_backup.sh)

Fitur pengaman:

1. Hanya bekerja di folder `2026-10-12--07-19`; menerima argumen lokasi khusus jika backup tidak ada di path default. Nama folder wajib sama dengan `name` dalam `backup.json`.
2. Mengharuskan `type=raw`, `hashAlgorithm=SHA-256`, tujuh hash berbentuk 64 digit heksadesimal; memakai parser sederhana untuk format JSON Kernel Flasher (bukan parser umum semua JSON).
3. Menolak file image yang hilang, kosong, atau berupa symlink. Membaca ukuran file dan SHA-256 tujuh file dengan `sha256sum`.
4. Bila ada kesalahan, mencetak `BACKUP_FILE_VERIFICATION=FAILED` dan status penyebab. Bila semua cocok, `BACKUP_FILE_VERIFICATION=PASS`.
5. Tidak menggunakan akses blok, `dd`, flashing, restore, perubahan root, perubahan slot atau jaringan/upload. Jangan menganggap hasil PASS sebagai sertifikasi boot/restore.

**Uji dengan fixture sintetik:** tujuh image benar → `PASS`; satu berubah →
`FAIL_HASH_MISMATCH`; satu image hilang → `IMAGE_MISSING_OR_NOT_REGULAR_FILE`.
CI: [test-backup-checker.yml](../.github/workflows/test-backup-checker.yml).

### Cara menjalankan di Termux

**1. Download lalu baca isinya** (gunakan URL branch `dev/rothko`):

```sh
curl -fL --proto '=https' --tlsv1.2 \
  'https://raw.githubusercontent.com/cogan17/Xiomi-14t-pro/dev/rothko/scripts/verify_kernel_flasher_backup.sh' \
  -o "$HOME/verify_kernel_flasher_backup.sh"
cat "$HOME/verify_kernel_flasher_backup.sh"
```

**2. Konfirmasi folder, tanpa mengubah isinya:**

```sh
su -c 'ls -lah /sdcard/KernelFlasher/backups/2026-10-12--07-19'
```

**3. Jika folder cocok, jalankan verifikasi:**

```sh
su -c 'sh /data/data/com.termux/files/home/verify_kernel_flasher_backup.sh'
```

**Keluaran:** bagi hasil teks `verified=...`, `failed=...` dan
`BACKUP_FILE_VERIFICATION=...` beserta status setiap file.
Bila nama folder ternyata lain, **jangan tebak atau paksa**: laporkan
path yang ditemukan untuk direview sebelum eksekusi.

Proses hashing `system_dlkm.img` atau `vendor_dlkm.img` berpotensi
memerlukan waktu beberapa menit jika ukurannya besar. Jangan tutup
Termux saat verifikasi berlangsung.

### Setelah verifikasi

- `PASS` hanya memvalidasi checksum berkas terhadap metadata dari
  **folder yang sama**, bukan terhadap kondisi runtime kernel yang terbaru.
- Simpan backup utuh beserta `backup.json` di penyimpanan kedua
  (PC/SSD/USB), lalu verifikasi salinannya. Jangan unggah image mentah,
  backup rahasia, atau log berisi ID perangkat ke repository publik.
- Jangan me-restore `init_boot_a` Rothko hanya karena hash Degas aktif
  sudah diketahui. Root BakaSU dan kelangsungan boot masih harus dijaga.
- Tidak menyimpulkan penyebab Slot B `Unbootable` dari hasil file backup.

**Referensi:** [audit Slot A](ROTHKO_ACTIVE_SLOT_A_AUDIT.md);
[status proyek](PROJECT_STATUS.md);
[insiden](INCIDENTS.md).
