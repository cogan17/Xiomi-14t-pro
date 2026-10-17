# Kernel Xiaomi 14T Pro (rothko)

Kernel khusus **Xiaomi 14T Pro** (`rothko`, MediaTek Dimensity 9300+ / MT6989), dibangun di repo ini.

**Sumber gabungan (keputusan owner 2026-10-16, D-017, D-019):** kernel dibangun dari **GKI 6.1 (GKID)**, yang sudah terbukti boot di rothko. Ada tiga acuan: **kernel bawaan rothko** (ACK resmi `android14-6.1-2025-06_r11`, versi `6.1.138`), **GKID**, dan **GKI 2.0 (ACK android14-6.1)**. Setiap build, kernel dicek otomatis terhadap kernel bawaan rothko dan terhadap **BSP Xiaomi di repo ini**: daftar simbol KMI MediaTek/Xiaomi, generasi KMI, dan `gki_defconfig`. Mesin build-nya adalah **milik repo ini**: branch `rothko-engine`, salinan mesin [cogan17/Cogan](https://github.com/cogan17/Cogan) (D-021). Commit yang dipakai dipin di `rothko/engine.lock` (`TARGET_DEVICE=rothko`). Pengembangan rothko tidak menyentuh repo Cogan.

> [!CAUTION]
> Siapkan `boot.img` stock yang **sama persis** dengan versi HyperOS Anda sebelum flash. Langkah pemulihan ada di bagian **[Pulihkan dari bootloop](#pulihkan-dari-bootloop)** di bawah.

---

## Isi build rothko

| | |
|---|---|
| Root manager | **KernelSU Next + SUSFS**, **BakaSU + SUSFS**, atau **keduanya** dalam satu run (ZIP terpisah) |
| Fitur | SUSFS, NoMount, Baseband Guard (BBG), BBRv3 (`bbr` dan `bbr3`) + paket jaringan, LTO pilihan (KSUN + SUSFS: Full LTO) |
| Kernel | 6.1 dari salah satu **sumber kernel**: **GKID 6.1** (sublevel **167–177**, `lts` = terbaru) atau **kernel bawaan rothko** (ACK resmi `6.1.138`, sublevel tetap). Lihat *Dua sumber kernel* |
| Nama | `Cogan-Rothko` (GKID) atau `Cogan-Rothko-ACK` (kernel bawaan) di versi kernel (mis. `6.1.177-Cogan-Rothko-r4-…`), nama ZIP, banner flasher dan nama rilis |
| Pengaman | ZIP AnyKernel3 memakai cek perangkat (`do.devicecheck=1`, `device.name1=rothko`): di HP lain proses flash berhenti dengan *Unsupported device* sebelum `boot` disentuh |
| Gate KMI | Setelah compile, `scripts/kmi_compat.py` (mesin `rothko-engine`) memastikan kernel tetap cocok dengan modul vendor HP (lihat *Kompatibilitas*). Gagal = build berhenti, tidak ada ZIP |
| Revisi & waktu | **Build Revision** (`r` + angka) dan **Build Time** sama seperti varian lain |

---

## Cara build

**Actions → Cogan Rothko Kernel Builder (GKI 6.1 + BSP check) → Run workflow** di repo ini, lalu isi:

| Isian | Pilihan untuk rothko |
|---|---|
| Root Manager | `KernelSU Next + SUSFS`, `BakaSU + SUSFS`, atau `KSUN + SUSFS & BakaSU + SUSFS` |
| LTO Package | `fullLTO + NoMount + Clean LTO` (wajib untuk KSUN + SUSFS) |
| Sumber kernel | `GKID 6.1 (Ahmed Al-Nassif)` (default) atau `Kernel bawaan rothko (ACK resmi 6.1.138)` |
| Kernel Sublevel | GKID: `lts` atau angka 167–177, pilih yang **sama atau lebih baru** dari kernel stock (`6.1.138` di HyperOS `OS3.0.301.0`). Kernel bawaan: `lts` atau `138` |
| Build Revision | mis. `r4` |
| Build Time | `N` atau waktu tetap |
| Networking, BBG | biarkan aktif (KSUN + SUSFS selalu aktif) |

Form hanya menawarkan KernelSU Next + SUSFS, BakaSU + SUSFS, atau keduanya. Kombinasi yang tidak valid ditolak sebelum kompilasi, misalnya KSUN + SUSFS tanpa Full LTO, sublevel GKID di bawah 167, atau sublevel selain `138` untuk kernel bawaan.

---

## Dua sumber kernel (D-020)

Acuan owner ada tiga: kernel bawaan rothko, GKID, dan GKI 2.0 (ACK android14-6.1). Karena itu ada dua pilihan **sumber kernel**. Fitur Cogan sama di keduanya: KSUN/BakaSU + SUSFS, NoMount, BBG, BBRv3 (`bbr`/`bbr3`), LTO, Build Revision dan Build Time. Gate KMI-nya juga sama, dengan tiga acuan.

| | GKID 6.1 (default) | Kernel bawaan rothko |
|---|---|---|
| Sumber | [GKI-Duchamp-6.1](https://github.com/ahmed-alnassif/GKI-Duchamp-6.1) (Ahmed Al-Nassif), android14-6.1-lts | ACK resmi Google tag `android14-6.1-2025-06_r11`, commit `6ab8c9a8`, **sumber yang sama dengan kernel bawaan HP** (`6.1.138-android14-11-g6ab8c9a86a33`) |
| Sublevel | 167–177 (lebih baru dari stok) | 138 (sama dengan stok) |
| Tambahan dasar | Tumpukan patch GKID: *force-load* modul, protected exports dihapus, patch performa | Hanya bagian kompatibilitas: *force-load* modul dan protected exports dihapus. Tanpa patch performa GKID, jadi ABI-nya paling dekat dengan stok |
| Status | 6.1.177 sudah boot di HP (KSUN + SUSFS r2/r3) | Lolos compile lokal + gate KMI. **Belum diuji di HP** |

Patch Cogan untuk kernel bawaan hanya beda konteks, isinya sama. Ada dua patch yang diadaptasi:
- **SUSFS 002**: blok include di `fs/exec.c`, `fs/namespace.c` dan `fs/proc/base.c`;
- **BBRv3**: satu hunk di `tcp_input.c`.

Isi perubahannya dicek per berkas dan identik dengan versi GKID. Tree hasilnya dikunci seperti sublevel GKID.

---

## Kenapa dari GKI, bukan dari sumber kernel Xiaomi?

HP GKI seperti rothko memisahkan kernel dan driver: partisi `boot` hanya berisi kernel generik Android (GKI), sedangkan driver MediaTek/Xiaomi ada di modul `vendor_dlkm` yang dimuat lewat antarmuka stabil (KMI `android14-6.1`). Jadi "kernel khusus rothko" adalah kernel GKI yang cocok dengan KMI HP ini.

| | Sumber BSP Xiaomi (repo ini, `bsp-rothko-u-oss`) | GKI 6.1 (GKID) |
|---|---|---|
| Versi | `6.1.57`, **lebih tua** dari kernel stock HP (`6.1.138-android14-11`) | `6.1.160`–`6.1.177`, sama atau lebih baru dari stock |
| Sublevel | Tetap | Bisa dipilih |
| Root + SUSFS | Belum pernah terkompilasi (kompilasi PR #8 gagal) | KSUN + SUSFS dan BakaSU + SUSFS **sudah boot di rothko** (uji HP owner 2026-10-16) |

Karena itu kernel dibangun dari GKI. BSP tetap dipakai sebagai acuan wajib di setiap build: gate KMI memeriksa bahwa kernel GKI mengekspor **semua** simbol dari daftar MTK/Xiaomi milik BSP (cek 2026-10-16: MTK 3353/3353, Xiaomi 308/308), generasi KMI-nya sama (11), dan semua opsi `=y` di `gki_defconfig` BSP juga aktif. Ada empat pengecualian yang sudah ditinjau: `DEBUG_STACK_USAGE`, `MEDIA_CEC_RC`, `UAPI_HEADER_TEST` dan `MODULE_SCMVERSION`. Opsi terakhir hanya atribut modinfo/sysfs `scmversion`, dan mati karena mesin mematikan `LOCALVERSION_AUTO` demi nama versi Cogan; temuan run pertama 38934173981.

---

## Fitur yang digabung (GKI + BSP)

| Dari | Fitur | Cara masuk ke HP |
|---|---|---|
| Cogan (GKI 6.1) | KernelSU Next / BakaSU, SUSFS, NoMount, Baseband Guard, BBRv3 (`bbr`/`bbr3`) + paket jaringan, Full/Thin LTO, patch performa GKID | Di dalam `Image` (partisi `boot`) |
| Xiaomi / MediaTek | Semua driver dan fitur HP: kamera, layar, modem, audio, termal, sensor, charging, dll (268 modul `vendor_dlkm` + 60 `system_dlkm`) | Tetap modul stock di HP; kernel Cogan wajib cocok KMI-nya (gate di bawah) |
| BSP Xiaomi (repo ini) | Daftar simbol MTK/Xiaomi, generasi KMI, `gki_defconfig`, hook vendor | Dicek otomatis setiap build sebagai acuan |
| Kernel bawaan rothko (ACK `6.1.138`) | Daftar simbol MTK/Xiaomi versi stok, generasi KMI, `gki_defconfig`, hook vendor, ABI beku yang dipakai modul vendor HP | Diambil otomatis saat build (commit dipin), dicek sebagai acuan |

Hasil penelusuran isi BSP terhadap GKID 6.1.177 (2026-10-16):
- **Tidak ada fitur Xiaomi/MediaTek di inti kernel BSP yang hilang dan dibutuhkan.** File yang hanya ada di BSP adalah kode lama yang sudah dihapus upstream: staging `rtl8712`, `a2mp`, qdisc `atm`/`cbq`/`dsmark`, berkas `OWNERS`.
- **8 hook vendor** hanya ada di BSP (mis. `android_vh_allow_domain_state`, yang di ACK sudah di-*revert* Google). Tidak satu pun dipakai modul vendor, karena tidak ada di daftar simbol mana pun.
- Trace event `mtk_fuse` di `fs/fuse` hanya instrumentasi debug, juga sudah dihapus di ACK yang lebih baru, dan tidak dipakai modul vendor.

Gate KMI memeriksa ketiga hal ini setiap build. Bila kelak ada hook BSP yang **dipakai** modul vendor tetapi tidak ada di kernel GKI, build berhenti.

### Acuan kernel bawaan rothko

Kernel bawaan HP (`6.1.138-android14-11-g6ab8c9a86a33-ab14396278`) adalah ACK resmi Google, tag `android14-6.1-2025-06_r11` (commit `6ab8c9a8`, publik di [aosp-mirror/kernel_common](https://github.com/aosp-mirror/kernel_common)). Mesin Cogan mengambil bagian yang dibutuhkan gate (±10 MB, commit dipin) **sebelum** compile. Gate lalu memeriksanya seperti BSP, ditambah jumlah CRC yang berbeda terhadap ABI beku kernel bawaan, yaitu ABI yang dipakai saat modul vendor HP dibangun.

Hasil cek lokal 2026-10-16 (6.1.167 + paritas dan 6.1.177):
- semua simbol stok diekspor: MTK 3596/3596, Xiaomi 455/455;
- generasi KMI 11;
- 6 hook vendor hanya ada di kernel bawaan, dan tidak satu pun dipakai modul vendor;
- CRC berbeda 538, himpunannya sama persis di 167 dan 177 (kernel yang sudah boot di HP).
- Hanya satu opsi `=y` bawaan yang tidak ada di GKID: `MEMFD_ASHMEM_SHIM`. Opsi ini **dicabut Google sendiri** dari android14-6.1 (ACK `8e481acd`, 2026-03-10: hanya diperlukan di kernel 6.12+) dan tidak mengekspor simbol apa pun, jadi tidak dipasang ulang (D-019).

---

## Kompatibilitas dengan modul vendor rothko

Driver MediaTek/Xiaomi di HP adalah modul `vendor_dlkm` (versi stock `6.1.138-android14-11`). Kernel Cogan hanya layak dicoba di HP bila modul itu tetap bisa dimuat. Prinsipnya **kompatibel dulu, flash belakangan**.

| Syarat | Cara Cogan memastikannya |
|---|---|
| Generasi KMI sama (`11`) | Gate KMI membaca `KMI_GENERATION` dari sumber |
| Semua simbol yang dipakai modul MediaTek dan Xiaomi diekspor | Gate KMI mencocokkan `android/abi_gki_aarch64`, `_mtk` dan `_xiaomi` dengan `vmlinux.symvers`. Simbol yang hilang tidak bisa dipaksa, jadi build gagal |
| Modul GKI bertanda tangan Google tetap bisa mengekspor simbol (WiFi, dll.) | `android/abi_gki_protected_exports_*` dihapus: sudah begitu di GKID 177, ditambahkan Cogan untuk sublevel lain (*paritas GKID*) |
| Beda CRC simbol tidak menolak modul | Perubahan *force-load* GKID di `kernel/module/version.c` (paritas GKID untuk sublevel lain). Jumlah CRC yang beda dari ABI beku tetap dilaporkan |

Hanya ujung GKID (6.1.177) yang membawa tumpukan patch GKID dari Ahmed; sublevel lebih lama adalah android14-6.1-lts murni. Karena itu Cogan memasang padanannya (`kernel-patches/common`, penghapusan protected exports) pada sublevel tersebut, dan untuk KSUN + SUSFS hasilnya ikut dikunci sebagai tree akhir.

Ringkasan gate muncul di ringkasan run (`KMI …: OK; … BSP: …; stock 6.1.138: …`) dan di `kmi-compat-rothko.json` pada artifact `build-env-…`.

---

## Sublevel

Semua varian SUSFS (KSUN, BakaSU, KernelSU) butuh **6.1.167 ke atas**: patch kernel SUSFS memerlukan konteks `fs/namespace.c` (include `trace/hooks/blk.h` dan hook vendor `do_new_mount_fc`) yang baru ada di 6.1.167. Di 160–166 patch itu gagal, jadi pilihan tersebut ditolak di awal run. Patch tidak pernah diadaptasi diam-diam.

KSUN + SUSFS dibangun dari kandidat yang sudah diuji di HP. Patch-nya diterapkan tanpa *fuzz*, dan tiap sublevel punya tree hasil yang dikunci di `configs/ksun-susfs-6.1-features.lock.json` → `sublevels` (branch `rothko-engine`). Build berhenti bila tree berbeda.

- **167–177**: terverifikasi. 177 tetap identik byte-per-byte dengan build yang lolos uji HP.
- **160–166**: tidak tersedia (alasan di atas).

Menambah sublevel baru (di branch `rothko-engine`): ambil pin-nya dari `configs/upstream.lock` Cogan (`git cherry-pick` commit **Cogan Manual Update**, lihat `ENGINE.md`), lalu:

```sh
git init -q /tmp/gkid && git -C /tmp/gkid fetch --depth=1 https://github.com/ahmed-alnassif/GKI-Duchamp-6.1 <commit>
python3 scripts/ksun_susfs_sublevel.py record /tmp/gkid <commit>
```

Salin JSON hasilnya ke `sublevels` di lock `rothko-engine` (PR ke branch itu), lalu naikkan `ENGINE_COMMIT` di `rothko/engine.lock`, build, dan uji. Bila patch tidak cocok, alat ini berhenti dan sublevel itu tetap tidak tersedia.

---

## Flash dan pulihkan

1. Flash `1-KERNEL_Cogan-Rothko-…zip` dengan [Kernel Flasher](https://github.com/fatalcoder524/KernelFlasher) (fatalcoder524). Yang diubah hanya partisi `boot`.
2. Pasang APK manager dari artifact/rilis yang sama (2 **atau** 3) dan modul NoMount (4).
3. Bootloop: flash `boot.img` stock lewat fastboot, lihat [Pulihkan dari bootloop](#pulihkan-dari-bootloop).

---

## Mesin build sendiri (D-021)

Mesin build ada di branch **`rothko-engine`** repo ini. Branch itu salinan cogan17/Cogan `d9cbc9f` beserta sejarahnya; asal-usul dan kreditnya ada di `ENGINE.md`.

- `rothko/engine.lock` (di `dev/rothko`) menunjuk satu commit branch itu (`ENGINE_REPO=cogan17/Xiomi-14t-pro`, `ENGINE_COMMIT`). Workflow menolak lock yang menunjuk repo lain.
- File workflow ada di branch default agar tombol **Run workflow** muncul (D-018). Lock dan acuan BSP dibaca dari `dev/rothko`.
- Perubahan rothko (patch, pin, gate) dikerjakan lewat PR ke `rothko-engine`, lalu `ENGINE_COMMIT` dinaikkan lewat PR ke `dev/rothko`. Build lama tetap bisa diulang dari commit yang sama.
- Perbaikan umum dari Cogan disalin dengan `git cherry-pick`, bukan merge.
- Cache ccache dibaca dari rilis `ci-ccache-store` repo ini. Belum ada cache berarti build dingin, lebih lambat beberapa menit.
- Satu-satunya sumber daya Cogan yang masih dibaca (hanya-baca) adalah rilis `cogan-mirror`, berisi manager BakaSU *spoofed*.

---

## Pulihkan dari bootloop

Diadaptasi dari Panduan Bootloop Cogan, bagian *Khusus Xiaomi 14T Pro (rothko)*.

| | |
|---|---|
| Codename | `rothko` |
| SoC | MediaTek Dimensity 9300+ (MT6989) |
| Partisi | A/B (slot `_a` / `_b`) |
| Kernel stock | GKI `android14-6.1` (contoh `6.1.138-android14-11`) |
| ROM | HyperOS (contoh `OS3.0.301.0.WNNIDXM`) |

**Flash `boot` atau `init_boot`?** Flash **`boot`** saja. HP ini dirilis dengan Android 14, jadi kernel ada di partisi `boot`; `init_boot` hanya berisi ramdisk, dan ZIP rothko tidak pernah mengubahnya. `init_boot.img` stock hanya perlu di-flash juga jika Anda pernah mem-patch `init_boot` sendiri (Magisk atau KernelSU mode LKM).

**Masuk fastboot:** tahan **Volume Bawah + Power** sampai muncul tulisan **FASTBOOT**.

**Langkah:**

1. Pastikan `boot.img` berasal dari versi HyperOS yang **sama persis** dengan yang terpasang.
2. Jalankan `fastboot flash boot boot.img`, lalu `fastboot reboot`.
3. HP menyala dengan kernel stock, dan data tetap aman.

**Jangan pernah:**

- Menjalankan `flash_all_lock` dari ROM fastboot. Skrip ini mengunci bootloader; dengan partisi yang sudah diubah, HP bisa mati total (*hard brick*).
- Mem-flash ROM yang **lebih lama** dari versi terpasang. Xiaomi memakai anti-rollback, dan downgrade bisa membuat HP mati total.
- Memakai SP Flash Tool atau mode BROM MediaTek. Biasanya butuh akun resmi Xiaomi, dan bisa menghapus kalibrasi modem/IMEI.
- Mem-flash `boot.img` ke partisi lain (`init_boot`, `vendor_boot`, dan seterusnya).

Recovery bawaan Xiaomi (**Volume Atas + Power**) tidak bisa mem-flash `boot.img`, jadi gunakan fastboot.

**Masih bootloop setelah flash `boot.img` stock?**

1. Flash ROM fastboot resmi dengan versi yang sama memakai `flash_all_except_storage` (data tetap ada).
2. Jika tetap gagal, bawa ke service center resmi Xiaomi.
