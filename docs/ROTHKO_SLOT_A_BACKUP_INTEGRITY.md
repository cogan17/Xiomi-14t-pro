# Tahap 9 — Verifikasi integritas backup RAW Kernel Flasher

**Tanggal persiapan:** 12 Oktober 2026  
**Status pembaruan 12 Oktober 2026: tujuh image backup `07-19` telah diperiksa langsung setelah diunggah pengguna, dan semuanya `SHA-256 PASS 7/7`.** Ini adalah audit byte dari *file yang diunggah*, bukan pemeriksaan tersendiri terhadap salinan lain pada HP atau perangkat eksternal. Skrip Termux yang sebelumnya dibuat tidak perlu dijalankan lagi untuk memvalidasi salinan yang sudah diperiksa di sini.

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

## Hasil inspeksi visual terbaru: video File Manager+ (12 Oktober 2026)

Pengguna mengirim video layar berdurasi sekitar 11 detik.
Folder `KernelFlasher/backups/2026-10-12--07-19` dibuka di File Manager+.
Terdapat tepat **8 entri** berikut menurut daftar tampilan:

| Nama file | Ukuran menurut File Manager+ |
|---|---:|
| `backup.json` | 874 B |
| `boot.img` | 67,11 MB |
| `dtbo.img` | 8,39 MB |
| `init_boot.img` | 8,39 MB |
| `system_dlkm.img` | 7,47 MB |
| `vbmeta.img` | 8,39 MB |
| `vendor_boot.img` | 67,11 MB |
| `vendor_dlkm.img` | 21,97 MB |

**Interpretasi:** file manager menampilkan ketujuh image dan
`backup.json` pada folder 07.19, sesuai log `Backup ... saved` yang
sudah dilaporkan. Ukuran dibulatkan menurut tampilan aplikasi; **bukan**
hasil pengukuran ukuran byte lengkap atau verifikasi checksum.

**Tahap yang masih menunggu:** jalankan verifikator *read-only*
untuk membaca tiap file dan membandingkan dengan `backup.json`
yang **ada di folder 07.19**, bukan memakai JSON dari folder 02.40.
Sejauh ini belum ada hasil `verified=7 / failed=0` dari HP.

**Larangan tetap:** jangan mem-flash, restore, mengganti slot,
atau menghapus file backup lama hanya karena file-file ini terlihat.

## HASIL FINAL BERDASARKAN FILE YANG DIUNGGAH — 12 Oktober 2026

Pengguna mengunggah **delapan file nyata** dari backup Kernel Flasher
`2026-10-12--07-19`: `backup.json` + ketujuh `.img`.
Semua file diakses **secara read-only** pada lingkungan pemeriksaan.
SHA-256 dihitung secara independen dari seluruh isi tiap berkas dengan
`hashlib.sha256` yang membaca file dalam potongan 4 MiB, lalu dibandingkan
dengan `hashes` pada `backup.json`.

Metadata: `name=2026-10-12--07-19`, `type=raw`,
`hashAlgorithm=SHA-256`, kernel
`6.1.177-android14-11-Cogan #1 SMP PREEMPT 2026-10-10 03:36:04 UTC`,
`bootSha1=82d969f0cab5e7f17f5d499b847e7cba64a08932`.

| Berkas image | Ukuran byte terukur | SHA-256 dihitung dari berkas terunggah | Metadata cocok? |
|---|---:|---|:---:|
| `boot.img` | 67,108,864 | `f39b666ead0c5a740a652c62225e343222b4e5fc89a560ff8f850eebf4cf6f8a` | **PASS** |
| `dtbo.img` | 8,388,608 | `47954740b3e890e0414cc5e5fc0f495c9750fe117d81f3607171d6b65c5eaff7` | **PASS** |
| `init_boot.img` | 8,388,608 | `951f096146157773abe4cbbd9b0dacbe9c2fa6400d4c438298353e5fb8a8bf04` | **PASS** |
| `system_dlkm.img` | 7,471,104 | `361be1dfdf7fa5d84f4712e005d4d1925100b3e94cf04954619fd45ba18defda` | **PASS** |
| `vbmeta.img` | 8,388,608 | `bfe79b5ba411e927943b8b918d802dd02ed751da384d4d7752e7e6b19c32b526` | **PASS** |
| `vendor_boot.img` | 67,108,864 | `087e76586bb981bbd1f37334f68707bac1f3b81d9a88caa452a9433feb76a384` | **PASS** |
| `vendor_dlkm.img` | 21,970,944 | `596cce7cd8e8a4a44c47080ce914facc9580004b5c18a8627c90551a3da5d536` | **PASS** |

**TOTAL = 188,825,600 bytes (~180.08 MiB); hasil 7/7 PASS,
0 mismatch, 0 file hilang**. `backup.json` berukuran 874 byte.

### Pemeriksaan berlapis terhadap bukti sebelumnya

- Hash kelima image (`boot`, `init_boot`, `vendor_boot`,
  `dtbo`, `vbmeta`) **juga cocok** dengan pembacaan langsung partisi
  aktif Slot A via Termux pada tahap sebelumnya.
- **Dua image DLKM** cocok dengan hash dalam metadata Kernel Flasher
  `07-19`; kedua hash tersebut juga pernah tercatat dalam metadata
  `02-40`, tetapi **belum** dicocokkan dengan hash langsung partisi
  via Termux.
- `init_boot.img` merupakan **stock Degas** menurut perbandingan hash
  dengan arsip `OS3.0.301.0.WNEIDXM.zip` yang sudah diaudit;
  `vendor_boot.img` identik dengan stock Rothko WNNIDXM.
- `boot.img` cocok hash Cogan yang dilaporkan dari partisi Slot A,
  tetapi **belum** dibandingkan byte-per-byte dengan artefak r7 dari
  GitHub; jangan menyatakan provenance artefak sepenuhnya terbukti.

### Batas keamanan yang masih berlaku

- **Integritas salinan yang dikirim: TERBUKTI** terhadap metadata
  SHA-256 Kernel Flasher. Ini bukan sertifikasi bahwa restore image
  apa pun pasti aman.
- Kami **belum** menguji boot dari image yang dipulihkan, kecocokan
  ABI/KMI keseluruhan, atau ketahanan terhadap bootloop.
- Ketersediaan dan integritas **salinan kedua di PC/SSD/USB** belum
  terverifikasi. Simpan backup mentah dan JSON tanpa modifikasi, kemudian
  verifikasi lagi di media kedua.
- Backup Slot B dan alasan indikator `Unbootable` merupakan topik
  terpisah. Jangan melakukan pergantian slot/flash untuk mencobanya.
- **Tidak ada file image mentah yang diunggah ke repository GitHub**;
  hanya ukuran, hash, dan kesimpulan teknis dipublikasikan.

Keputusan tahap berikutnya: **pertahankan Slot A yang sekarang berfungsi**;
simpan salinan backup independen sebelum membahas penggantian
`init_boot_a` Degas ke Rothko.

## Tahap 10 — Salinan backup independen di Windows / Steam Deck

**Status: menunggu tindakan pengguna.** Tujuh image yang dikirim sudah
diverifikasi terhadap `backup.json` (7/7 SHA-256 PASS). Namun belum ada
bukti bahwa *salinan lain* di PC/SSD telah dibuat dan diverifikasi.

1. Hubungkan Xiaomi 14T Pro ke Windows dengan kabel data, dan pilih
   **Transfer file** pada notifikasi USB Android.
2. Buka File Explorer: perangkat Xiaomi → penyimpanan internal →
   `KernelFlasher/backups/2026-10-12--07-19`.
3. **COPY**, jangan **MOVE**. Tempel seluruh folder, termasuk
   `backup.json` dan tujuh `.img`, misalnya ke
   `C:\CoganBackups\2026-10-12--07-19` atau SSD eksternal.
4. Buka PowerShell di PC, sesuaikan variabel folder di bawah, dan
   bandingkan SHA-256 salinan dengan tujuh hash yang sudah diverifikasi
   secara independen dari file sumber.

```powershell
$folder = 'C:\CoganBackups\2026-10-12--07-19'
$expected = [ordered]@{
  boot        = 'f39b666ead0c5a740a652c62225e343222b4e5fc89a560ff8f850eebf4cf6f8a'
  dtbo        = '47954740b3e890e0414cc5e5fc0f495c9750fe117d81f3607171d6b65c5eaff7'
  init_boot   = '951f096146157773abe4cbbd9b0dacbe9c2fa6400d4c438298353e5fb8a8bf04'
  system_dlkm = '361be1dfdf7fa5d84f4712e005d4d1925100b3e94cf04954619fd45ba18defda'
  vbmeta      = 'bfe79b5ba411e927943b8b918d802dd02ed751da384d4d7752e7e6b19c32b526'
  vendor_boot = '087e76586bb981bbd1f37334f68707bac1f3b81d9a88caa452a9433feb76a384'
  vendor_dlkm = '596cce7cd8e8a4a44c47080ce914facc9580004b5c18a8627c90551a3da5d536'
}
$passed = 0
foreach ($name in $expected.Keys) {
  $file = Join-Path $folder ($name + '.img')
  if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
    Write-Output "$name : FILE_HILANG"
    continue
  }
  $actual = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
  if ($actual -eq $expected[$name]) {
    Write-Output "$name : PASS"
    $passed++
  } else {
    Write-Output "$name : MISMATCH"
  }
}
Write-Output "verified=$passed/7"
```

Interpretasi: `verified=7/7` berarti tujuh file image salinan di
lokasi PC/SSD sama SHA-256-nya dengan set yang telah diperiksa.
Jangan menghapus backup asli dan jangan menganggap lulus hash sebagai
jaminan pemulihan perangkat. Pastikan `backup.json` ikut tersalin
dan dapat dibuka; skrip ringkas ini membandingkan ketujuh image terhadap
hash acuan independen, bukan menguji mekanisme restore.

**Belum terverifikasi:** pengguna belum mengirim output PowerShell
dari salinan PC/SSD. Tidak ada tindakan terhadap slot atau root.

## Bukti transfer flashdisk melalui MT Manager (video 12 Oktober 2026)

**Sumber:** rekaman layar baru pengguna berdurasi sekitar 65 detik.
Konteksnya adalah backup Kernel Flasher untuk Slot A yang telah lolos
pemeriksaan isi SHA-256 **7/7** pada salinan yang sebelumnya diunggah.

**Yang teramati di rekaman:**

- Pengguna mengakses penyimpanan eksternal USB OTG dari MT Manager
  (volume memiliki mount path di bawah `/storage/`, identitas volume
  tidak dipublikasikan di dokumen ini).
- Menyalin **folder `KernelFlasher`** dari penyimpanan internal ke
  penyimpanan eksternal. Dialog salin memperlihatkan progres sekitar
  **180,08 MiB** hingga akhirnya tertutup dan file explorer kembali.
- Pada sisi USB terlihat folder `KernelFlasher/backups/2026-10-12--07-19`.
- Di dalamnya terlihat `backup.json` dan tujuh berkas:
  `boot.img`, `dtbo.img`, `init_boot.img`,
  `system_dlkm.img`, `vbmeta.img`, `vendor_boot.img`,
  `vendor_dlkm.img`. Ukuran file yang ditampilkan konsisten
  dengan hasil audit asal (dibulatkan oleh File Manager).
- Pengguna membuka `backup.json` dari folder USB; nama backup,
  identitas kernel Cogan 6.1.177 dan daftar SHA-256 tampil dalam editor.

**Kesimpulan yang dapat ditarik:** salinan di USB **sudah dilakukan dan
isi folder terlihat**, bukan hanya rencana. Tetapi **belum ada
penghitungan ulang SHA-256 dari byte yang tersimpan di USB**.
Ini berarti integritas file **asal yang diunggah** terverifikasi 7/7,
sementara integritas **salinan USB** masih menunggu verifikasi independen.

### Verifikasi salinan USB tanpa penulisan partisi

Gunakan skrip `scripts/verify_kernel_flasher_backup.sh` yang sudah
ada dan telah diuji dalam GitHub Actions. Berikan path folder USB
sebagai argumen, bukan menggunakan lokasi default internal HP.

```sh
# Ganti <USB_ID> dengan nama volume yang terlihat pada perangkat.
su -c 'ls -lah /storage/<USB_ID>/KernelFlasher/backups/2026-10-12--07-19'
su -c 'sh /data/data/com.termux/files/home/verify_kernel_flasher_backup.sh /storage/<USB_ID>/KernelFlasher/backups/2026-10-12--07-19'
```

Target yang **belum dikonfirmasi**: `verified=7`, `failed=0`,
`BACKUP_FILE_VERIFICATION=PASS`. Jika mount path berbeda, jangan
mencoba jalur disk atau operasi format/mount manual tanpa memeriksa
lokasi yang benar. Jika izin membaca USB gagal, laporkan error saja.

Tidak ada flashing, restore, perubahan slot/root, atau upload raw image
ke GitHub dalam tahap ini.
