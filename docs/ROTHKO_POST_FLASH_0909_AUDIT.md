# Audit setelah flash init_boot Rothko → Cogan r7 — 12 Oktober 2026

**Status pemeriksaan:** **SHA-256 ketujuh image dari backup baru PASSED (7/7)**. Image `init_boot.img` pada backup setelah reboot **identik byte-per-byte dengan stock Rothko WNNIDXM**, bukan stock Degas WNEIDXM. **Tidak berarti** seluruh fungsi root/modul telah teruji kembali.

## Kronologi yang disampaikan pengguna

1. Pengguna **sudah melakukan** flash `init_boot.img` Rothko, dilanjutkan instalasi ZIP kernel Cogan **r7** melalui Kernel Flasher. Ini adalah tindakan pengguna yang sudah terjadi, **bukan perintah/aksi dari proyek**.
2. Installer r7 menghasilkan log `ak3-log--2026-10-12--09-07.log`.
3. Perangkat direstart dan menurut pengguna **berhasil mencapai home screen**.
4. Pengguna membuat backup RAW Kernel Flasher yang baru, beridentitas **`2026-10-12--09-09`**, lalu mengunggah `backup.json` dan ketujuh `.img` untuk diperiksa.

## Metode pemeriksaan independen

- Hitung SHA-256 dengan membaca seluruh isi ketujuh file image dari unggahan, bukan hanya mempercayai metadata JSON.
- Bandingkan setiap hash hasil hitungan dengan **`backup.json` pukul 09.09**.
- Bandingkan dengan hash backup sebelum perubahan **07.19** yang telah diverifikasi sebelumnya.
- Buka isi `init_boot.img` langsung dari dua arsip firmware yang diserahkan pengguna, `OS3.0.301.0.WNNIDXM.zip` (rothko) dan `OS3.0.301.0.WNEIDXM.zip` (degas), hitung ulang SHA-256 keduanya.

## Hasil byte-for-byte

| Image setelah flash | Ukuran byte | SHA-256 hasil pembacaan file terbaru | Sama dengan 07.19? |
|---|---:|---|---|
| `boot.img` | 67,108,864 | `f39b666ead0c5a740a652c62225e343222b4e5fc89a560ff8f850eebf4cf6f8a` | **YA** |
| `dtbo.img` | 8,388,608 | `47954740b3e890e0414cc5e5fc0f495c9750fe117d81f3607171d6b65c5eaff7` | **YA** |
| `init_boot.img` | 8,388,608 | `4b25ce3f4a321b34aa5f84e7c8b0328065d7038c1a00b91fdcca7e0c17fe463f` | **TIDAK — berubah** |
| `system_dlkm.img` | 7,471,104 | `361be1dfdf7fa5d84f4712e005d4d1925100b3e94cf04954619fd45ba18defda` | **YA** |
| `vbmeta.img` | 8,388,608 | `bfe79b5ba411e927943b8b918d802dd02ed751da384d4d7752e7e6b19c32b526` | **YA** |
| `vendor_boot.img` | 67,108,864 | `087e76586bb981bbd1f37334f68707bac1f3b81d9a88caa452a9433feb76a384` | **YA** |
| `vendor_dlkm.img` | 21,970,944 | `596cce7cd8e8a4a44c47080ce914facc9580004b5c18a8627c90551a3da5d536` | **YA** |

**Hasil:** `verified=7`, `failed=0`; **1 image berubah, 6 tidak berubah**. Total tujuh image **188,825,600 byte**.

### Pembuktian identitas init_boot

| Sumber image | SHA-256 | Sama dengan image backup 09.09? |
|---|---|---|
| Stock **Rothko** `WNNIDXM` | `4b25ce3f4a321b34aa5f84e7c8b0328065d7038c1a00b91fdcca7e0c17fe463f` | **YA, identik** |
| Stock **Degas** `WNEIDXM` | `951f096146157773abe4cbbd9b0dacbe9c2fa6400d4c438298353e5fb8a8bf04` | **TIDAK** |

Backup sebelumnya 07.19 mengandung `init_boot` stock Degas. Setelah flash/reboot, backup 09.09 mengandung `init_boot` stock Rothko. Data ini menguatkan keberhasilan perpindahan image tanpa mengubah hash keenam image lainnya. **Klaim ini berbasis file backup yang diunggah sesudah reboot dan kronologi pengguna**, bukan pembacaan ulang langsung blok partisi dari Termux pada kesempatan yang sama.

## Audit log AnyKernel3 pukul 09.07

File log dari pengguna memuat:

- `Archive: .../android14-6.1.177-lts-r7-BakaSU-AnyKernel3.zip`
- `Installing...`, kemudian `/dev/block/by-name/boot_a`.
- Pembacaan `67108864 bytes`, format header 4, kernel `lz4_legacy`, ramdisk berukuran 0.
- `Repack to boot image` dan penulisan kembali 67,108,864 byte.
- Muncul **`ash: bad number`**, tetapi installer tetap melanjutkan dan menampilkan `Done!`.
- Banner installer masih menyebut **ReSukiSU/community/kernel source**; ini informasi branding template/package, bukan bukti jenis root kernel atau asal image yang benar-benar dijalankan.
- **Tidak ditemukan operasi penulisan `init_boot_a` dalam log r7 ini**. Karena pengguna mem-flash `init_boot` sebelum memasang r7, log r7 sendiri tidak mendokumentasikan langkah `init_boot` tersebut.

**Kesimpulan terpisah:** log menunjukkan proses AnyKernel3 menargetkan `boot_a` dan menyelesaikan run, namun peringatan `ash: bad number` sebaiknya diperiksa apabila ada kegagalan di masa depan. Hash `boot` pasca-boot sama dengan backup lama yang bekerja; jangan menyimpulkan bahwa run sepenuhnya tanpa warning.

## Batas bukti dan langkah berikutnya

**Terbukti oleh checksum:** image `init_boot` backup 09.09 **stock Rothko**, keenam image lain tidak berubah. **Dilaporkan pengguna:** restart berhasil masuk home screen.

**Belum dikonfirmasi ulang setelah reboot:**
- BakaSU Manager/kernel driver masih cocok versinya; mode root GKI/built-in, `su` masih berfungsi, dan SELinux masih Enforcing.
- SUSFS, NoMount/MetaModule, Zygisk dan **16 modul** benar-benar aktif/berfungsi, bukan hanya tertinggal dalam direktori.
- Suhu baterai/SoC dalam pemakaian berkelanjutan dan kompatibilitas OTA.
- Backup **09.09** sudah disalin ke flashdisk dan diverifikasi **di USB**. Pengujian USB 7/7 sebelumnya hanya mencakup folder **07.19** yang memiliki image Degas.
- Isi aktual semua partisi lain di luar tujuh image snapshot serta keamanan restore.

**Tindak lanjut aman:** jangan flash lagi hanya untuk pengujian. Periksa BakaSU, SUSFS, NoMount, modul dan akses root secara read-only; pertahankan backup **07.19** (sebelum) dan **09.09** (sesudah) **dalam folder terpisah**, kemudian salin backup baru ke media eksternal dan verifikasi checksum bila diinginkan.

**Jangan membuang backup sebelum flash** hanya karena perangkat berhasil boot.
