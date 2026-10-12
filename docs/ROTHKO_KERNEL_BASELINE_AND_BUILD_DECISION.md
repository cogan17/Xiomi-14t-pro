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
| Target perangkat dan jalur GKI | Xiaomi 14T Pro `rothko`, Android 16; manifest/workflow GKI sebelumnya **meminta** Linux 6.1.177 / `android14-11`. Catatan `docs/ROTHKO_LINEAGE.json` menyatakan `compiled_kernel_commit_confirmed=false`, `true_running_kernel_version_verified=false`, dan `uname` dapat ter-spoof SUSFS. **Jangan klaim kernel aktif adalah 6.1.177 tanpa bukti perangkat.** |
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

## Workflow diagnostik yang sudah tersedia — manual saja

- **Tidak membuat workflow kompilasi baru.** `.github/workflows/rothko-bsp-compile-smoke.yml` dan `scripts/rothko_bsp_compile_smoke.sh` yang sudah ada diperbaiki pada branch PR #9. Saat ini perubahan tersebut **belum di-merge ke `dev/rothko`**; jangan menganggapnya sudah siap dijalankan dari branch yang dilindungi.
- Workflow hanya menerima **`workflow_dispatch` manual** pada `dev/rothko`. `stage=config` adalah default, hanya menghasilkan `out/.config` sementara pada runner. `stage=image` membutuhkan konfirmasi `DIAGNOSTIC`, menghasilkan `Image` sementara di runner dan mencatat checksum, **tidak mengunggah binari**.
- Kedua mode menolak bila branch modul resmi `MiCode/MTK_kernel_modules:bsp-rothko-u-oss` telah bergeser dari commit yang dicatat `a875701d71d29cfac0a9456c1e9c223d44f53d68`, agar sumber pasangan tidak berubah diam-diam. Ini **bukan** verifikasi ABI vendor.
- `build.config.constants` menetapkan `BRANCH=android14-6.1` dan `CLANG_VERSION=r487747c`; workflow diagnostik masih memakai **clang dari runner Ubuntu**, sehingga belum mereproduksi toolchain resmi. `build.config.common` menyatakan `KMI_GENERATION=11` dan defconfig GKI menyalakan `CONFIG_MODVERSIONS`, tetapi **CRC dan kompatibilitas modul vendor belum diuji**.
- Belum ada workflow yang otomatis mengkompilasi atau mengeluarkan paket siap flash akibat perubahan PR. Saat ini **hanya jalur persiapan**, bukan klaim build berhasil.

## Penghalang minimum yang masih terbuka

- Hubungan pasti `boot.img` dan versi kernel pada firmware aktif dengan base source/KMI; versi kernel yang sebelumnya dilaporkan harus dikonfirmasi sebelum membuat kandidat flash.
- Kesetaraan konfigurasi, `Module.symvers`/CRC simbol vendor dan `vendor_dlkm`/`system_dlkm` terhadap common build target.
- Port SUSFS resmi pada lima target patch Rothko, kepemilikan pre/post execve dan session FD otentik.
- G2 unwind late-load, G3 startup retry, G4/G5 status/lifetime shared credentials; status script tetap **BLOCKED**.
- Backup image pemulihan yang benar untuk slot aktif serta prosedur verifikasi hasil boot.

**PR #9 tetap Draft dan tidak di-merge.** Tidak perlu menunggu seluruh audit berulang selesai untuk mengerjakan *source alignment*, tetapi **jangan membuat kernel flashable dengan menebak basisnya**.
