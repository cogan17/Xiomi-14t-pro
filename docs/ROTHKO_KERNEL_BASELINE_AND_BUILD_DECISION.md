# Rothko — basis kernel dan keputusan build (12 Oktober 2026)

**Status: belum siap untuk build kandidat perangkat; PR #9 tetap Draft.**
Dokumen singkat ini menggantikan penambahan audit statis berulang dengan satu keputusan teknis yang dapat diuji. **Tidak ada merge, image, ZIP siap-flash, atau perubahan partisi.**

## Fakta yang diverifikasi

| Komponen | Sumber / keadaan |
|---|---|
| Source Cogan | `cogan17/Xiomi-14t-pro`, `dev/rothko@b2d8b54a0d8bb002d32dda24e58d2b5d0423546b`; `Makefile`: `VERSION=6`, `PATCHLEVEL=1`, `SUBLEVEL=57` |
| Baseline asli Xiaomi | `MiCode/Xiaomi_Kernel_OpenSource`, `bsp-rothko-u-oss@197c453d27da88f3b7b8fed7323ee6d15fc02066`; `Makefile` juga 6.1.57 |
| Modul vendor yang berpasangan | `MiCode/MTK_kernel_modules`, `bsp-rothko-u-oss@a875701d71d29cfac0a9456c1e9c223d44f53d68`; ada `gpu/mt6989` dan direktori `connectivity`, `fpsgo_cus`, `hbt_driver` |
| Struktur checkout lokal | `arch/arm64/boot/dts/mediatek` tidak memuat DTS `mt6989`/`rothko`; `drivers/misc/mediatek` tidak ada. Ini ciri pemisahan source common dan vendor, **bukan bukti kernel tidak dapat berjalan sebagai GKI**. |
| Perangkat saat pembahasan sebelumnya | Xiaomi 14T Pro `rothko`, HyperOS 3 / Android 16, KMI `android14-11`; Cogan r7 dilaporkan menggunakan Linux 6.1.177. **Verifikasi ulang build aktif dan modul vendor sebelum memilih tag build.** |
| Eksperimen root | `pershoot/KernelSU-Next@3438d6aa431f96a23f9e625bec3d53ce1fb14161`. Kandidat G1/G3 dan patch lain masih source-only; tidak terintegrasi. |
| SUSFS resmi | `simonpunk/susfs4ksu` berada di GitLab, pin semula `gki-android14-6.1@5192aa2d33b381b58c1051532f9e1dfa5de6e8d3`. Pengambilan/port tetap ditunda karena provenance/akses belum dapat diverifikasi. **Jangan mengganti dengan mirror tak diverifikasi.** |

Referensi resmi:
- https://github.com/MiCode/Xiaomi_Kernel_OpenSource/tree/bsp-rothko-u-oss
- https://github.com/MiCode/MTK_kernel_modules/tree/bsp-rothko-u-oss
- https://github.com/pershoot/KernelSU-Next

## Keputusan perubahan arah

1. **Jangan menambah lagi pengujian regresi yang mengulang risiko yang sudah diketahui.** Pertahankan CI existing sebagai guard pada perubahan source; tidak perlu membuat audit baru.
2. **Tentukan satu baseline kernel yang sesuai dengan firmware perangkat aktual.** Common 6.1.57 bukan pengganti otomatis bagi kernel perangkat 6.1.177. Sublevel saja tidak menentukan kompatibilitas; periksa KMI generasi `android14-11`, config, simbol/CRC `CONFIG_MODVERSIONS`, vendor/system_dlkm, dan boot image.
3. **Gunakan official MiCode vendor modules branch yang dipin sebagai sumber acuan**, bukan melakukan copy file SoC secara ad hoc ke common tree. Pemetaan build/ABI modul harus ada sebelum memutakhirkan common atau memakai kandidat hasil kompilasi.
4. Setelah baseline cocok, lakukan **compile-only/non-flash** untuk baseline tanpa KSUN/SUSFS sebagai langkah pengembangan pertama. Kegagalan toolchain/build perlu diperbaiki sebelum menambah fitur. Jangan memublikasikan artefak yang tampak siap-flash.
5. Setelah baseline benar dan compile-only sukses, selesaikan hook post-`execve` dan konflik SUSFS/KSUN yang nyata. Source-level patch applicability ≠ device compatibility. Port satu jalur integrasi yang dipilih, bukan memaksa GKI generik 6.1.177 dan source BSP 6.1.57 menjadi sama secara otomatis.
6. Perlu ada rencana pemulihan slot/partisi dan bukti ABI/KMI sebelum **uji perangkat**. **Tidak ada flashing otomatis**.

## Penghalang minimum yang masih terbuka

- Hubungan pasti `boot.img` dan versi kernel pada firmware aktif dengan base source/KMI; versi kernel yang sebelumnya dilaporkan harus dikonfirmasi sebelum membuat kandidat flash.
- Kesetaraan konfigurasi, `Module.symvers`/CRC simbol vendor dan `vendor_dlkm`/`system_dlkm` terhadap common build target.
- Port SUSFS resmi pada lima target patch Rothko, kepemilikan pre/post execve dan session FD otentik.
- G2 unwind late-load, G3 startup retry, G4/G5 status/lifetime shared credentials; status script tetap **BLOCKED**.
- Backup image pemulihan yang benar untuk slot aktif serta prosedur verifikasi hasil boot.

**PR #9 tetap Draft dan tidak di-merge.** Tidak perlu menunggu seluruh audit berulang selesai untuk mengerjakan *source alignment*, tetapi **jangan membuat kernel flashable dengan menebak basisnya**.
