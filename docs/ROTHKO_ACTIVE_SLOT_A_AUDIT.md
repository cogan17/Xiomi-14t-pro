# Tahap 8 — Fingerprint rantai boot Slot A (read-only)

**Status: HASIL TERKUMPUL dari HP, 12 Oktober 2026.** Skrip
read-only selesai di Termux tanpa flashing atau perubahan partisi.
**Metadata backup RAW Slot A bertanggal `2026-10-12--02-40` sudah diterima.**
SHA-256 lima partisi dalam `backup.json` cocok dengan pemeriksaan Termux,
namun berkas image cadangan individual **belum diterima/dihitung ulang**.
Ketersediaan serta integritas backup nyata masih perlu diverifikasi.

## Alasan pemeriksaan

HP Xiaomi 14T Pro (rothko) dengan firmware `OS3.0.301.0.WNNIDXM`
melaporkan Slot A aktif, Kernel Flasher menampilkan kernel image
`6.1.177-android14-11-Cogan`, BakaSU Manager/Driver berfungsi.

Pada 2026-10-12, checksum `init_boot_a` langsung dari perangkat
**cocok persis** dengan image stock **Degas** berukuran 8 MiB, bukan
image stock **Rothko**. Ini **bukan** bukti Slot A rusak ataupun
penjelasan otomatis untuk status Slot B `Unbootable`.

## Skrip yang akan dijalankan

[Lihat `scripts/collect_active_slot_a_hashes.sh`](../scripts/collect_active_slot_a_hashes.sh).

- Periksa `ro.product.device`, `ro.product.vendor.device` dan
  `ro.boot.slot_suffix`; berhenti kecuali `rothko` / `_a`.
- Pastikan target `/dev/block/by-name/*_a` berupa perangkat blok dan
  ukuran setiap target masuk akal (antara 4 KiB dan 128 MiB);
  `init_boot_a` **harus 8 MiB**.
- Baca SHA-256 dari **`boot_a`, `init_boot_a`,
  `vendor_boot_a`, `dtbo_a`, `vbmeta_a`**. Tidak menulis image
  maupun membuat salinan partisi.
- Bandingkan secara persis hanya pada ukuran penuh yang sama:
  `boot`, `init_boot`, `vendor_boot` dengan stock ZIP Rothko;
  `init_boot` dengan stock ZIP Degas; `dtbo` dan `vbmeta`
  dengan backup mentah Slot B yang diserahkan pengguna.
- **`dtbo_b` belum terbukti stock**; kecocokan DTBO hanya berarti
  sama dengan **backup Slot B**, bukan pasti benar/aman.
- `vbmeta_b` raw dari backup berukuran 8 MiB, sedangkan berkas
  stock dalam firmware ZIP 12 KiB; checksum satu partisi utuh tidak
  otomatis sebanding dengan SHA-256 berkas yang dipotong.

## Perintah Termux setelah melihat skrip

```sh
curl -fL --proto '=https' --tlsv1.2 \
  'https://raw.githubusercontent.com/cogan17/Xiomi-14t-pro/dev/rothko/scripts/collect_active_slot_a_hashes.sh' \
  -o "$HOME/collect_active_slot_a_hashes.sh"
cat "$HOME/collect_active_slot_a_hashes.sh"
su -c 'sh /data/data/com.termux/files/home/collect_active_slot_a_hashes.sh'
```

**Jangan** menjalankan skrip shell langsung melalui `curl | sh`.
Bila `blockdev` atau pembacaan partisi tidak tersedia, skrip mencetak
status kegagalan/skip: jangan mengakali kondisi tersebut dengan menulis
ulang partisi. Membaca partisi yang aktif adalah operasi baca berukuran
puluhan MiB dan bisa memakan waktu.

## Sesudah menerima keluaran

Catat setiap ukuran, SHA-256, identitas firmware, dan klasifikasi. Jangan
memutuskan image aman-flash dari SHA saja. Kemudian **konfirmasi apakah
backup Slot A terbaru sudah tersedia** dari Kernel Flasher (yang
terdokumentasi dengan `backup.json` dan image asli) sebelum menyusun
opsi pemulihan. Jika backup lama diambil sebelum flashing r7,
backup tersebut **bukan** gambaran Slot A sekarang.

**Belum diizinkan:** restore stock Rothko ke `init_boot_a`,
menghapus root, mem-flash ZIP GKI, mematikan SUSFS, atau mengganti
status Slot B. Keberhasilan checksum dan root saat ini tidak menjamin
ABI/KMI/AVB cocok.

Laporan terkait:
[audit active init_boot](ROTHKO_ACTIVE_INIT_BOOT_AUDIT.md),
[backup Slot B](ROTHKO_SLOT_B_BACKUP_AUDIT.md),
[status proyek](PROJECT_STATUS.md).

## Hasil nyata: kelima partisi Slot A aktif

Data dari `su -c 'sh /data/data/com.termux/files/home/collect_active_slot_a_hashes.sh'`:

```text
device=rothko
vendor_device=rothko
active_slot=_a
firmware=OS3.0.301.0.WNNIDXM
```

| Partisi | Ukuran (byte) | SHA-256 dari HP | Perbandingan |
|---|---:|---|---|
| `boot_a` | 67108864 | `f39b666ead0c5a740a652c62225e343222b4e5fc89a560ff8f850eebf4cf6f8a` | **Tidak identik** dengan stock Rothko yang telah diaudit. Kernel Flasher sebelumnya menampilkan `6.1.177-android14-11-Cogan`, tetapi belum dicocokkan byte-for-byte dengan artefak r7 GitHub. |
| `init_boot_a` | 8388608 | `951f096146157773abe4cbbd9b0dacbe9c2fa6400d4c438298353e5fb8a8bf04` | **Identik** dengan stock **Degas WNEIDXM**, bukan stock Rothko WNNIDXM. |
| `vendor_boot_a` | 67108864 | `087e76586bb981bbd1f37334f68707bac1f3b81d9a88caa452a9433feb76a384` | **Identik** dengan stock Rothko WNNIDXM. |
| `dtbo_a` | 8388608 | `47954740b3e890e0414cc5e5fc0f495c9750fe117d81f3607171d6b65c5eaff7` | **Identik** dengan backup raw Slot B. ZIP pembanding tidak memuat DTBO, jadi belum dibuktikan sebagai stock. |
| `vbmeta_a` | 8388608 | `bfe79b5ba411e927943b8b918d802dd02ed751da384d4d7752e7e6b19c32b526` | **Identik** dengan backup raw Slot B. Backup B sudah diuji: 12.288 byte awal sama dengan file stock WNNIDXM dan selebihnya padding nol. |

Semua partisi di atas dapat dibaca oleh skrip; tidak ada error ukuran
atau pembacaan yang dilaporkan. Metode: `blockdev --getsize64` dan
`sha256sum` langsung dari perangkat blok, tanpa menulis/mencadangkan image.

### Kesimpulan yang dibenarkan bukti

- Ada **susunan boot campuran** pada Slot A: `boot_a` non-stock
  (dan kernel kustom sebelumnya ditunjukkan oleh Kernel Flasher),
  `init_boot_a` berisi stock **Degas**, `vendor_boot_a` stock **Rothko**,
  serta `dtbo_a` dan `vbmeta_a` cocok dengan backup Slot B.
- Sistem masih boot di Slot A; BakaSU masih digunakan menurut bukti
  sebelumnya. **Hasil hash tidak membuktikan kerusakan hardware**.
- **Tidak ada bukti bahwa image Degas menyebabkan Slot B ditandai
  unbootable.** Data kontrol slot dan kompatibilitas semua partisi
  tetap belum lengkap.
- SHA `boot_a` berbeda dari stock sesuai dugaan adanya kernel kustom,
  tetapi tidak cukup untuk mengidentifikasi versi file r7 yang
  sebenarnya tanpa membandingkan artefak/backup penuh.
- `dtbo_a == dtbo_b` hanya menunjukkan kedua backup/partisi cocok.
  Jangan menyatakan DTBO ini “benar-benar stock” tanpa pembanding
  firmware yang sesuai.
- `vbmeta_a == vbmeta_b` dan cocok dengan konten stock dalam backup B
  tidak membuktikan seluruh status AVB/keamanan boot.

### Keputusan selanjutnya: backup Slot A sebelum pemulihan

**Langkah berikutnya yang disarankan adalah membuat/mengecek backup RAW
lima partisi Slot A menggunakan fasilitas Backup pada Kernel Flasher**,
lalu memverifikasi hasil checksum `boot`, `init_boot`, `vendor_boot`,
`dtbo`, `vbmeta` dan menyimpannya di luar HP. Ini harus dilakukan
tanpa memilih Flash, Restore, Change Slot, Unmount ataupun Reboot.

Jika backup baru belum ada, **jangan** menimpa `init_boot_a` dengan
stock Rothko atau mengambil keputusan kehilangan root. Kesamaan hash
tidak menggantikan berkas cadangan. Jangan unggah image mentah ke repo
publik; simpan metadata/checksum saja.

**Tidak dilakukan dalam tahap ini:** flashing, modifikasi/root removal,
perubahan slot, backup image aktif, atau pemeriksaan ABI mendalam.

## Bukti baru: `backup.json` Slot A — 12 Oktober 2026, 02.40

Pengguna mengirim metadata Kernel Flasher `backup.json` sebagai tindak lanjut
permintaan backup aktif. Nama backup `2026-10-12--02-40`, tipe `raw`,
algoritma SHA-256. Identitas kernel yang tercatat:

```text
kernelVersion=6.1.177-android14-11-Cogan #1 SMP PREEMPT 2026-10-10 03:36:04 UTC
bootSha1=82d969f0cab5e7f17f5d499b847e7cba64a08932
```

| Nama dalam metadata | SHA-256 di `backup.json` | Perbandingan dengan hash perangkat |
|---|---|---|
| `boot` | `f39b666ead0c5a740a652c62225e343222b4e5fc89a560ff8f850eebf4cf6f8a` | **Cocok** dengan Termux `boot_a` |
| `init_boot` | `951f096146157773abe4cbbd9b0dacbe9c2fa6400d4c438298353e5fb8a8bf04` | **Cocok** dengan Termux `init_boot_a` (stock Degas) |
| `vendor_boot` | `087e76586bb981bbd1f37334f68707bac1f3b81d9a88caa452a9433feb76a384` | **Cocok** dengan Termux `vendor_boot_a` (stock Rothko) |
| `dtbo` | `47954740b3e890e0414cc5e5fc0f495c9750fe117d81f3607171d6b65c5eaff7` | **Cocok** dengan Termux `dtbo_a` |
| `vbmeta` | `bfe79b5ba411e927943b8b918d802dd02ed751da384d4d7752e7e6b19c32b526` | **Cocok** dengan Termux `vbmeta_a` |
| `system_dlkm` | `361be1dfdf7fa5d84f4712e005d4d1925100b3e94cf04954619fd45ba18defda` | **Baru**, belum diukur independen pada perangkat |
| `vendor_dlkm` | `596cce7cd8e8a4a44c47080ce914facc9580004b5c18a8627c90551a3da5d536` | **Baru**, belum diukur independen pada perangkat |

### Tingkat kepastian dan pembatasan

**Terverifikasi:** isi `backup.json` sudah dibaca; 5/5 SHA-256
`boot/init_boot/vendor_boot/dtbo/vbmeta` cocok dengan keluaran Termux
read-only sebelumnya. Identitas kernel Cogan dan SHA-1 boot selaras
dengan screenshot Kernel Flasher Slot A.

**Belum terverifikasi:** 7 berkas image asli yang dirujuk metadata
**tidak diunggah bersama `backup.json`**; belum ada SHA-256 yang
dihitung ulang dari file backup tersimpan, ukuran berkasnya, atau
bukti backup disalin ke penyimpanan terpisah. **Tidak benar** untuk
mengatakan "backup lengkap aman" hanya dari file JSON. `system_dlkm`
dan `vendor_dlkm` juga belum memiliki pembanding hash dari Termux.

**Langkah aman:** pengguna memastikan ketujuh berkas image ada di lokasi
backup Kernel Flasher, dihitung SHA-256 **file**-nya tanpa flashing,
dan hasilnya cocok dengan metadata. Simpan set backup lengkap beserta
`backup.json` di lokasi lain. Hindari publikasi image mentah di GitHub.

**Tetap ditahan:** pemulihan `init_boot_a`, perubahan slot, flashing
GKI/ROM lain, atau tindakan yang dapat mengganggu root BakaSU.

## Bukti tambahan: screenshot backup 07.19 pada 12 Oktober 2026

Screenshot Kernel Flasher yang baru diterima menunjukkan log:

```text
Saving backup 2026-10-12--07-19
Saving boot
Saving dtbo
Saving init_boot
Saving system_dlkm
Saving vbmeta
Saving vendor_boot
Saving vendor_dlkm
Backup 2026-10-12--07-19 saved
```

**Bukti yang didukung screenshot:** aplikasi melaporkan selesai menyimpan
backup baru bernama `2026-10-12--07-19`, mencakup tujuh partisi yang
disebutkan. Ini **berbeda** dari backup `2026-10-12--02-40` yang metadata
`backup.json`-nya sudah dicocokkan dengan Termux.

**Yang belum terbukti:** screenshot ini bukan tampilan isi folder.
Belum ada daftar file, ukuran file, `backup.json` pukul 07.19, ataupun
hash SHA-256 hasil pembacaan **berkas backup 07.19**. Tampilan log saja
tidak membuktikan data pemulihan tersedia dan utuh. Screenshot juga
tidak menampilkan label slot secara eksplisit; keterkaitan dengan Slot A
mengikuti konteks bahwa sebelumnya Slot A aktif, bukan verifikasi
terpisah mengenai target backup.

**Tindak lanjut:** buka folder `2026-10-12--07-19` melalui file
manager, pastikan `backup.json` dan tujuh image tersimpan, kemudian
hitung ulang SHA-256 file di folder itu dan bandingkan dengan
`backup.json` yang **berasal dari folder yang sama**. Pertahankan
backup 02.40 tanpa menimpa, dan salin backup lengkap ke lokasi berbeda
setelah terverifikasi. Tidak perlu flashing, restore atau mengubah slot.
