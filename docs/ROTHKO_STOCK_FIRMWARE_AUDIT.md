# Audit firmware stock Xiaomi 14T Pro (rothko)

**Tanggal audit:** 12 Oktober 2026  
**Metode:** membaca dua ZIP yang diunggah pengguna, tanpa memasang atau mengubah image.  
**Status:** referensi dokumentasi; **BUKAN izin flashing atau bukti kompatibilitas perangkat**.

## Identitas paket

| Parameter | Paket yang sesuai dengan Rothko | Paket yang berbeda perangkat |
|---|---|---|
| ZIP | `OS3.0.301.0.WNNIDXM.zip` | `OS3.0.301.0.WNEIDXM.zip` |
| Metadata `pre-device` | `rothko` | `XIG07\|degas` |
| Versi firmware dalam metadata | `OS3.0.301.0.WNNIDXM` | `OS3.0.301.0.WNEIDXM` |
| Security patch level yang tercantum | `2026-06-01` | `2026-03-01` |
| Platform tertulis pada `vbmeta.img` | `mt6989` | `mt6897` |
| ZIP SHA-256 | `6272901ed6719dc1c3274a28d2fa980ca8d05adeb20d5d520f19df9caf663398` | `3f6ee6e07590b38829bea8a308a4281dc2a8ae7f584b23c38e18180eca144c91` |
| Pemeriksaan CRC ZIP | Lulus seluruh entri | Lulus seluruh entri |

**Peringatan:** WNEIDXM/`degas` tidak boleh digunakan sebagai pengganti firmware
WNNIDXM/`rothko`, khususnya image boot/vendor_boot/preloader/vbmeta.
CRC hanya menunjukkan tidak ditemukan kerusakan data ZIP, **bukan**
pembuktian autentikasi atau tanda tangan resmi.

## Inventaris dan checksum image dari WNNIDXM

| Image | Ukuran | SHA-256 |
|---|---:|---|
| `boot.img` | 67.108.864 byte | `d8fa7c0baa2de9d6a5590c6ad2515b52fd04a32d8b2f49055a44f8864b9de4c2` |
| `init_boot.img` | 8.388.608 byte | `4b25ce3f4a321b34aa5f84e7c8b0328065d7038c1a00b91fdcca7e0c17fe463f` |
| `vendor_boot.img` | 67.108.864 byte | `087e76586bb981bbd1f37334f68707bac1f3b81d9a88caa452a9433feb76a384` |
| `vbmeta.img` | 12.288 byte | `6361d8c6d5ff50818833bf8e3c3ace69cfdadb608989f145d84b5764ab35e846` |
| `vbmeta_system.img` | 4.096 byte | `0460ec654545c3997d44e335bb2aac1034f459135eef7064c2cb623be13f42cd` |
| `vbmeta_vendor.img` | 4.096 byte | `cf551785428120872fb4b47a5a7fb0d003858a5941311812cdd1cb3de44c52c4` |
| `preloader_raw.img` | 909.312 byte | `7328c0a6a75e2242faedd334cc7e176b6b3d2fc1886211e42ecb8b9579bf5ed3` |

Berkas `vendor_dlkm.img` dan `dtbo.img` **tidak ada** dalam kedua ZIP
yang diperiksa; ini tidak membuktikan bahwa partisinya tidak ada di perangkat.

## Header dan versi kernel di dalam boot stock

- `boot.img` dan `init_boot.img`: Android boot image header **v4**.
- `vendor_boot.img`: vendor boot image header **v4**.
- Kernel stock dalam `WNNIDXM/boot.img` terkompresi **LZ4 legacy**.
  String `Linux version` dari kernel yang didekompresi secara lokal:

  `6.1.138-android14-11-g6ab8c9a86a33-ab14396278`

- Identitas tersebut cocok dengan teks **Kernel Flasher Slot B** pada
  screenshot yang diberikan pengguna. Hal ini **tidak membuktikan** bahwa
  image Slot B identik byte demi byte atau aman di-boot; screenshot
  juga menunjukkan **Unbootable: Yes** dan **Successful: No**.

## Mengapa init_boot dari model berbeda dapat terlihat bisa dipatch oleh LKM?

Image `init_boot.img` dari kedua ZIP sama-sama berukuran 8 MiB, mempunyai
header v4 dan ramdisk yang hampir identik. Perbandingan byte-ke-byte
menemukan **87 byte berbeda** di seluruh image. Ini dapat menjelaskan
mengapa root manager mampu memproses ramdisk dari image model lain.

**Kemampuan mem-patch bukan bukti aman dipasang atau boot sukses.**
Gunakan image stock **rothko** yang sesuai dengan firmware perangkat.
Versi modul LKM, tanda tangan/AVB, status slot dan dependensi vendor
tetap harus diperiksa secara terpisah.

## Hubungan dengan proyek kernel Cogan

- **6.1.138:** versi kernel stock yang diverifikasi *di dalam ZIP WNNIDXM*;
  **bukan klaim tentang kernel aktif** pada HP.
- **6.1.170:** angka yang pernah tampil pada `uname`; menurut pengguna
  ini adalah **SUSFS-spoofed**, bukan bukti versi kernel sebenarnya.
- **6.1.177:** target dan paket GKI yang dibuat proyek
  [Cogan GKI BakaSU SUSFS](https://github.com/cogan17/GKI_BakaSU_SUSFS);
  kesamaan dengan kernel yang aktif perlu bukti tersendiri.
- **6.1.57:** versi `Makefile` pada source Xiaomi di
  [Xiomi-14t-pro](https://github.com/cogan17/Xiomi-14t-pro).
- `android14-11` adalah identitas keluarga GKI/KMI pada build stock;
  kecocokan ABI/CRC simbol dan modul `vendor_dlkm` belum diverifikasi.

## Batas keamanan / tindak lanjut

Tidak ada file partisi asli yang diunggah ke GitHub dalam audit ini.
Tidak ada perintah flashing, patch root, atau modifikasi perangkat.
Pemeriksaan *build provenance*, modul vendor, konfigurasi board,
slot aktif, dan checksum image yang sedang terpasang masih diperlukan
sebelum menyatakan kernel eksperimen aman.

**Backup stock** sebaiknya disimpan terpisah dan tidak ditimpa hasil patch.
