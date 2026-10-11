# Tahap 8 — Fingerprint rantai boot Slot A (read-only)

**Status:** skrip dan CI disiapkan; **belum dijalankan pada HP**.
Perintah pada tahap ini **tidak** memulihkan atau mem-flash partisi.

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
