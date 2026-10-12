# Audit pasca-flash metode init Rothko → Cogan r7 (12 Oktober 2026)

**Bukti diterima:** log AnyKernel3 pukul **09.07** dan backup RAW Kernel Flasher `2026-10-12--09-09` lengkap: `backup.json` dan tujuh `.img`. Pengguna melaporkan sudah mem-flash stock `init_boot.img` Rothko **lebih dahulu**, lalu Cogan r7, kemudian reboot berhasil sampai home screen dan membuat backup baru.

**Status file backup baru: 7/7 PASS** setelah menghitung **SHA-256 ulang secara independen dari seluruh byte ketujuh file yang diunggah**, bukan hanya menyalin nilai `backup.json`. Tidak ada penulisan partisi selama analisis ini.

## Perbandingan backup sebelum dan sesudah

| Image | Ukuran byte | SHA-256 terbaru | Dibandingkan backup `07-19` |
|---|---:|---|---|
| `boot.img` | 67,108,864 | `f39b666ead0c5a740a652c62225e343222b4e5fc89a560ff8f850eebf4cf6f8a` | **Sama**: image Cogan r7 |
| `init_boot.img` | 8,388,608 | `4b25ce3f4a321b34aa5f84e7c8b0328065d7038c1a00b91fdcca7e0c17fe463f` | **BERUBAH** dari stock Degas ke **stock Rothko WNNIDXM** |
| `vendor_boot.img` | 67,108,864 | `087e76586bb981bbd1f37334f68707bac1f3b81d9a88caa452a9433feb76a384` | Sama |
| `dtbo.img` | 8,388,608 | `47954740b3e890e0414cc5e5fc0f495c9750fe117d81f3607171d6b65c5eaff7` | Sama |
| `vbmeta.img` | 8,388,608 | `bfe79b5ba411e927943b8b918d802dd02ed751da384d4d7752e7e6b19c32b526` | Sama |
| `system_dlkm.img` | 7,471,104 | `361be1dfdf7fa5d84f4712e005d4d1925100b3e94cf04954619fd45ba18defda` | Sama |
| `vendor_dlkm.img` | 21,970,944 | `596cce7cd8e8a4a44c47080ce914facc9580004b5c18a8627c90551a3da5d536` | Sama |

Backup sebelumnya **`2026-10-12--07-19`**:
`init_boot.img` SHA-256 `951f096146157773abe4cbbd9b0dacbe9c2fa6400d4c438298353e5fb8a8bf04`
(stock **Degas WNEIDXM**).

Backup sesudah tindakan **`2026-10-12--09-09`**:
`init_boot.img` SHA-256 `4b25ce3f4a321b34aa5f84e7c8b0328065d7038c1a00b91fdcca7e0c17fe463f`
(stock **Rothko WNNIDXM** yang sudah diaudit pada ZIP firmware).

**Kesimpulan yang dibuktikan dari file:** tepat **1 dari 7 image** berubah, yaitu `init_boot.img`; keenam image lainnya identik SHA-256 dengan arsip `07-19`. Metadata `kernelVersion=6.1.177-android14-11-Cogan #1 SMP PREEMPT 2026-10-10 03:36:04 UTC` dan `bootSha1=82d969f0cab5e7f17f5d499b847e7cba64a08932` juga tidak berubah.

## Log flash kernel pukul 09.07

Dari `ak3-log--2026-10-12--09-07.log`:

- Installer membuka `android14-6.1.177-lts-r7-BakaSU-AnyKernel3.zip`.
- Alat AnyKernel3 menemukan `/dev/block/by-name/boot_a`; `GKI Kernel Supported: true`.
- Image `boot` header v4, kernel `lz4_legacy`, `RAMDISK_SZ [0]`; proses repack dan penulisan kembali 67,108,864 byte terlihat.
- Ada pesan `ash: bad number` setelah tahap `VBMETA`. **Peringatan non-fatal menurut alur log**: instalasi masih diteruskan sampai `Done!`. Jangan anggap penyebab/efek pesan ini diketahui sebelum mengaudit skrip installer.
- Log **tidak** mencatat flash stock `init_boot` sebelumnya; keberhasilan tahap itu didukung oleh laporan pengguna dan perubahan hash pada backup terbaru.
- Log tidak membuktikan BakaSU/SUSFS/NoMount dan semua modul bekerja saat runtime setelah reboot.

## Status dan pengaman setelah reboot

Pengguna **melaporkan berhasil masuk home screen** dan membuat backup RAW sesudah flashing. Ini bukti boot awal berhasil, **bukan** bukti tidak ada bug, kompatibilitas ABI/AVB penuh, atau seluruh modul aktif.

**Belum diperiksa setelah perubahan:** identitas Driver/Manager BakaSU, SUSFS, NoMount, 16 modul aktif, suhu di idle/beban normal, dan indikator Slot B.

**Langkah aman berikutnya:** lihat halaman utama Manager dan daftar modul (atau inventaris read-only yang sudah ada); verifikasi backup `09-09` dalam salinan USB terpisah. **Jangan menimpa/menghapus backup `07-19`** karena merupakan bukti kondisi sebelum perubahan. Arsip baru ini belum diverifikasi pada flashdisk.

**Tidak dilakukan oleh audit:** flash, restore, patch, reboot, ubah slot, ubah modul, atau upload file image mentah ke repository publik.
