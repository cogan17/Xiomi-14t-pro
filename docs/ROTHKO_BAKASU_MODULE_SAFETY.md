# Tahap 11 — Perlindungan BakaSU, SUSFS, NoMount dan seluruh modul

**Tanggal:** 12 Oktober 2026  
**Status 12 Oktober 2026:** skrip inventaris **sudah dijalankan di perangkat**. Terdapat 16 direktori modul dan semua berstatus enabled-on-disk, tanpa penanda disable/remove. **Modul dan pengaturannya belum dicadangkan secara terpisah**. Audit fungsi runtime belum selesai.  
**Perangkat:** Xiaomi 14T Pro (`rothko`), Android 16, firmware WNNIDXM.

> **Gerbang keselamatan:** tidak ada operasi flash, restore,
> penggantian slot, penghapusan modul, atau perubahan konfigurasi root
> sebelum analisis modul dan rencana pemulihan matang.

## Fakta dasar yang sudah didukung bukti

- Kernel Flasher menunjukkan Slot A aktif dengan image
  `6.1.177-android14-11-Cogan`, status `Successful: Yes`.
- BakaSU Manager `v4.2.0-rc3 (35222/5)` dan kernel driver
  `v4.2.0-rc3-5b76b884 (35222/5)` sesuai nomor versi yang ditampilkan.
  SUSFS melaporkan `v2.3.0`; SELinux `Enforcing`.
- Snapshot `boot_a`, `init_boot_a`, `vendor_boot_a`, `dtbo_a`,
  `vbmeta_a`, `system_dlkm`, `vendor_dlkm` memiliki **backup
  RAW utuh 7/7 SHA-256 PASS**, termasuk salinan terpisah di USB OTG.
  Rincian: [audit backup](ROTHKO_SLOT_A_BACKUP_INTEGRITY.md).
- `init_boot_a` saat ini **identik dengan stock Degas** menurut
  pemeriksaan byte. `vendor_boot_a` identik dengan stock Rothko.
  Tidak boleh menyimpulkan penyebab status Slot B Unbootable dari bukti ini.
- Screenshot lama BakaSU menampilkan badge modul **16**, dan audit
  Termux terbaru kini mengonfirmasi **16 direktori modul**. Kesamaan
  hitungan bukan bukti fungsi runtime modul.

## Dua kategori modul yang TIDAK boleh disamakan

| Lapisan | Contoh | Lokasi/backup | Risiko jika boot chain berubah |
|---|---|---|---|
| **Modul root BakaSU** | Modul systemless, skrip saat boot, modifikasi SELinux/properti, Zygisk, SUSFS helper, modul yang bergantung pada MetaModule | Umumnya di `/data/adb/modules` dan konfigurasi lain di `/data/adb`. **Belum dicadangkan oleh backup tujuh image partisi.** | Bisa tidak aktif meskipun file modul masih ada; dapat bergantung pada root, injeksi, mount atau interface kernel. |
| **Modul kernel `.ko`** | Driver MediaTek dan tambahan dari `system_dlkm`/`vendor_dlkm` | Image `system_dlkm.img` dan `vendor_dlkm.img` sudah terverifikasi 7/7. | Harus cocok dengan interface kernel/KMI/CRC symbol; `vermagic` beda bukan bukti pasti rusak. |
| **NoMount/MetaModule** | Mekanisme pemasangan systemless atau modul metamount (jika memang terpasang) | Lokasi dan konfigurasi aktual masih harus ditemukan dari metadata instalasi; jangan menganggap ada hanya dari nama folder. | Modul systemless bisa tidak dimount/aktif jika MetaModule/kernel tidak cocok. |
| **Pengaturan root pribadi** | Akses superuser aplikasi, preferensi Manager, konfigurasi modul, data aplikasi yang dipakai modul | Tidak termasuk backup `boot` dan `*_dlkm`. **Belum diinventarisasi**; sering mengandung data sensitif. | Berpotensi hilang jika proses recovery menyentuh data atau implementasi root diganti. |

**Penting:** menulis stock Rothko `init_boot.img` ke Slot A
secara teknis biasanya tidak menimpa isi `/data/adb/modules`.
Namun **tidak menjamin BakaSU dan modul tetap berfungsi saat boot**;
fungsi modul dapat bergantung pada komponen root/kernel/ramdisk,
MetaModule, SELinux, dan properti perangkat.

## Tahap A — inventaris privat, hanya baca

Skrip: [`scripts/collect_bakasu_module_inventory.sh`](../scripts/collect_bakasu_module_inventory.sh).

Skrip akan menolak perangkat selain Rothko dan slot aktif bukan A;
menuntut izin baca root lalu mengamati:

- ID, nama, versi/versionCode dari `module.prop` pada
  `/data/adb/modules` (tanpa membaca isi skrip atau data modul).
- Flag `disable`, `remove`, `service.sh`,
  `post-fs-data.sh`, `system.prop`, `sepolicy.rule`,
  `zygisk/`, dan `skip_mount`.
- Keberadaan folder tambahan `modules_update`, `ksu`,
  `metamodule`, `nomount`, `service.d`, dan `post-fs-data.d`
  **hanya sebagai petunjuk**, bukan bukti aktivasi.
- Jumlah file `.ko` di direktori module system/vendor dan
  jumlah baris `/proc/modules` (tidak memaksa load/unload).

Perintah Termux — unduh, **baca dulu**, kemudian jalankan:

```sh
curl -fL --proto '=https' --tlsv1.2 \
  'https://raw.githubusercontent.com/cogan17/Xiomi-14t-pro/dev/rothko/scripts/collect_bakasu_module_inventory.sh' \
  -o "$HOME/collect_bakasu_module_inventory.sh"
cat "$HOME/collect_bakasu_module_inventory.sh"
su -c 'sh /data/data/com.termux/files/home/collect_bakasu_module_inventory.sh'
```

**Privasi:** daftar modul dapat mengungkap aplikasi atau konfigurasi
sensitif. Tinjau keluaran sebelum dibagikan. **Jangan commit hasil
inventaris pribadi ke repository publik** dan jangan mengirim file
`/data/adb` mentah, daftar izin superuser atau data aplikasi ke GitHub.
Jika perlu membahas publik, gunakan ringkasan kategori dan status saja.

## Tahap B — checklist pemulihan yang belum dilakukan

1. Pastikan modul apa saja yang **sekarang** terpasang/disabled dan
   memiliki skrip boot, mount, Zygisk, NoMount atau ketergantungan SUSFS.
   Bandingkan dengan tampilan Manager; statistik direktori tidak
   menjamin modul benar-benar aktif saat runtime.
2. Setelah inventaris disetujui, rencanakan **backup terpisah** atas
   module ZIP installer yang dipakai, preferensi konfigurasi, serta
   data private module terkait. Simpan dengan izin/label SELinux yang
   benar bila perlu; jangan melakukan tar/copy membabi buta terhadap
   semua `/data/adb` tanpa meninjau data sensitif dan kompatibilitas
   waktu pemulihan. Setiap module mungkin berbeda.
3. Dokumen keamanan harus membedakan data instalasi modul, status
   pada root manager, pengaturan SU, data aplikasi dan file konfigurasi
   MetaModule/NoMount.
4. Evaluasi ketergantungan versi BakaSU `35222/5`, SUSFS `2.3.0`,
   mount/NoMount serta CRC/KMI driver MediaTek sebelum setiap rencana
   mengganti `init_boot_a`.
5. Jika di masa depan ada perubahan image, siapkan jalur recovery yang
   benar-benar dapat digunakan dan prosedur kembali ke **backup asli
   aktif**. Jangan menyamakan checksum PASS dengan jaminan bebas bootloop.
6. **Belum ada persetujuan flashing.** Hanya setelah seluruh risiko
   dan backup BakaSU+modul dinyatakan memadai kita diskusikan opsi
   pemulihan image Degas versus stock Rothko.

## Definisi sukses

Audit ini selesai jika: semua modul BakaSU yang penting telah
diinventarisasi, dependensi root/no-mount diidentifikasi,
rencana backup dan pemulihan konfigurasi modul tersedia,
dan pengguna memahami risiko yang tersisa. **Belum terpenuhi.**

## Hasil terbaru dari Termux: inventaris modul aktif (12 Oktober 2026)

**Sumber data:** keluaran langsung dari
`su -c 'sh /data/data/com.termux/files/home/collect_bakasu_module_inventory.sh'`.
Skrip dijalankan pada `rothko`, Slot A aktif, firmware
`OS3.0.301.0.WNNIDXM`, SELinux `Enforcing`.

**Privasi:** laporan publik ini sengaja tidak memuat ID/nama/versi
16 modul root atau data akses aplikasi. Inventaris terperinci terdapat
pada laporan pribadi pengguna. Hindari mengunggah isi `/data/adb`
ke repository publik.

| Metrik | Hasil dari perangkat |
|---|---:|
| Direktori modul di `/data/adb/modules` | **16** |
| Modul berstatus `enabled_on_disk` | **16** |
| Modul berstatus `disabled_on_disk` | **0** |
| Modul bertanda `remove` | **0** |
| Direktori modul tanpa `module.prop` | **0** |
| Modul memiliki `service.sh` | **12** |
| Modul memiliki `post-fs-data.sh` | **9** |
| Modul memiliki `system.prop` | **3** |
| Modul memiliki `sepolicy.rule` | **4** |
| Modul memiliki direktori `zygisk/` | **4** |
| Modul memiliki `skip_mount` | **0** |
| File `.ko` di `/vendor_dlkm/lib/modules` | **268** |
| File `.ko` di `/system_dlkm/lib/modules` | **60** |
| Baris `/proc/modules` saat audit | **519** |

Direktori tambahan yang **ada** di `/data/adb`:
`modules_update`, `ksu`, `metamodule`, `nomount`,
`service.d`, `post-fs-data.d`.

**Batas observasi:** keberadaan `modules_update` tidak membuktikan
ada pembaruan modul yang sedang menunggu. Keberadaan `metamodule` dan
`nomount` tidak dengan sendirinya menjelaskan versi, status runtime,
atau hubungan keduanya. `enabled_on_disk` tidak membuktikan
modul berhasil menjalankan skripnya saat boot; indikator direktori
`zygisk/` juga bukan satu-satunya cara modul menggunakan Zygisk.
Jumlah baris `/proc/modules` tidak boleh disamakan dengan jumlah
modul root maupun hanya jumlah `.ko` dari dua lokasi tersebut.

### Kelompok risiko untuk diperiksa secara privat

1. **Fondasi root dan mount:** BakaSU Manager/kernel driver,
   SUSFS, NoMount, MetaModule. Pastikan versi, kompatibilitas
   antarkomponen, metode mount, dan perilaku saat boot.
2. **Lingkungan Zygisk:** inventaris membuktikan ada modul berisi
   `zygisk/` dan modul terkait layanan boot. Integrasi/runtime harus
   diperiksa sebelum menyimpulkan ada konflik atau kecocokan.
3. **Kustomisasi dan pengendali perangkat:** beberapa modul memakai
   `service.sh`, `post-fs-data.sh`, atau `system.prop`; data
   konfigurasi di `/data` mungkin tidak tercakup backup partisi.
4. **Keamanan/perlindungan boot:** tanda `sepolicy.rule` atau layanan
   tidak menjamin kesesuaian setelah perubahan kernel/ramdisk. Modul
   pelindung bootloop sendiri tidak menjamin recovery dari bootloader.
5. **Driver `.ko`:** image `system_dlkm` dan `vendor_dlkm`
   sudah ada dalam backup partisi 7/7 PASS, tetapi kompatibilitas
   CRC simbol/KMI dengan kernel GKI yang berjalan masih belum tuntas.

### Hal yang masih perlu dilakukan sebelum mempertimbangkan restore

- Inventaris status dan ketergantungan **runtime** di BakaSU Manager
  (termasuk fitur NoMount, integrasi MetaModule dan Zygisk).
- Rencana cadangan privat untuk **modul dan konfigurasi**, terpisah
  dari tujuh image partisi. Perhatikan izin file, label SELinux,
  dan data yang sensitif. Tidak ada tindakan penyalinan/arsip modul
  dalam audit ini.
- Periksa installer module yang dapat dipakai untuk memulihkan
  versi yang sama jika diperlukan, beserta opsi recovery di luar HP.
- Evaluasi jalur kehilangan root saat `init_boot_a` diganti,
  dan jangan menganggap root akan hilang/bertahan dengan pasti
  hanya berdasarkan identitas image.
- **Tunda** flashing, restore, perubahan slot, reboot pengujian,
  atau pengubahan status 16 modul sampai dependensi diketahui.

**Status:** tahap inventaris metadata telah selesai; tahap
perlindungan konfigurasi modul dan uji runtime **BELUM** selesai.

## Penyederhanaan strategi: installer ZIP dahulu (kesepakatan 12 Oktober 2026)

Pengguna tidak membutuhkan backup penuh file dan konfigurasi seluruh
16 modul jika dapat memasangnya kembali. Strategi tahap selanjutnya
adalah **simpan installer ZIP versi yang sesuai secara offline,
lalu instal ulang jika diperlukan**.

- **Backup wajib yang sudah selesai:** tujuh image RAW Cogan r7
  dan salinan USB OTG, SHA-256 PASS 7/7.
- **Tahap belum dilakukan:** memeriksa bahwa pengguna benar-benar
  memiliki installer ZIP untuk 16 modul yang sedang dipakai;
  belum ada daftar hash ZIP atau salinan installer terverifikasi.
- **Pengecualian:** konfigurasi pribadi sulit direplikasi
  (contoh setelan ACC/Project Raco, integrasi Zygisk,
  konfigurasi modul yang memakai data aplikasi, ataupun kunci pribadi)
  mungkin **tidak pulih dari ZIP saja**. Cadangkan hanya jika memang
  ingin mempertahankan setelan tersebut dan jaga tetap privat.
- **Urutan pemulihan:** pulihkan root/kernel yang sesuai terlebih
  dahulu, lalu komponen mount/Zygisk yang kompatibel sesuai
  ketergantungan sebelum modul lain. Tidak ada urutan instalasi yang
  diklaim telah diuji untuk perangkat ini.
- **Batasan:** flash atau restore `init_boot_a` tidak otomatis
  menghapus `/data/adb/modules`, namun juga tidak menjamin fungsi
  BakaSU/modul tetap normal. Tidak boleh melakukan flashing berdasarkan
  kepemilikan ZIP semata.

**Keputusan operasional:** **tidak wajib mengarsipkan semua
`/data/adb`**, dan tidak perlu pengujian pemulihan masing-masing modul
pada tahap ini. Fokus pada ketersediaan installer,
catatan versi, dependensi penting dan jalur pemulihan
root/kernel yang benar. Status = direncanakan, belum diverifikasi.

## Bukti folder installer terorganisasi dari screenshot (12 Oktober 2026)

Pengguna memperlihatkan tiga screenshot File Manager pada
**Penyimpanan Utama → ARoot → modulKSU → Simpan**.
Dalam folder tersebut terdapat direktori yang dikelompokkan menurut
modul. Contoh kategori yang terlihat: pelindung bootloop, HyperUnlocked,
MetaModule, NavTweaks, Project Raco, SUSFS, Play Integrity Fix,
Tricky Store, Zygisk Next, dan modul Zygisk lainnya. Sebagian folder
tampak berisi lebih dari satu item. Ini merupakan **bukti
pengorganisasian arsip installer**, bukan bukti bahwa setiap folder
berisi ZIP versi yang saat ini terpasang.

**Penting:** tampilan lokasi bertuliskan `Penyimpanan Utama`;
belum ada bukti bahwa arsip `ARoot/modulKSU/Simpan` juga telah
disalin dan diverifikasi pada flashdisk. Status verifikasi 7/7
sebelumnya berlaku **hanya untuk backup tujuh image kernel**, bukan
folder installer modul.

Hal yang belum terlihat sebagai folder khusus pada screenshot:
ACC, YouTube Morphe, zygisk-detach, dan NoMount. Ini **bukan
klaim berkas hilang**: bisa tersimpan dalam kategori berbeda,
misalnya MetaModule, ataupun di folder lain.

**Rencana yang disederhanakan:**
- Pertahankan struktur direktori installer yang sudah dibuat pengguna.
- Cocokkan installer ZIP dan versi modul yang penting dengan daftar
  16 modul yang terdeteksi; tidak perlu backup penuh semua `/data/adb`
  jika pengguna bersedia instalasi ulang dan menyetel ulang.
- **Salin** (jangan pindahkan) folder installer ke flashdisk atau
  perangkat cadangan lain, kemudian cek keberadaan file dan checksum
  salinannya jika diperlukan. Jangan menghapus file asal.
- Periksa ulang konfigurasi pribadi yang sulit direkonstruksi secara
  terpisah, hanya jika memang dibutuhkan.
- Tidak ada izin flashing, restore, pengubahan root atau penghapusan
  modul akibat screenshot ini.

**Status:** penyimpanan installer terorganisasi secara visual;
kelengkapan ZIP versi terpasang dan integritas salinan eksternal
**belum diverifikasi**.

## Klarifikasi pengguna: subfolder menyimpan file ZIP installer

**Bukti baru:** screenshot File Manager membuka
`Penyimpanan Utama/ARoot/modulKSU/Simpan/TCP_Optimizer`.
Folder tersebut secara nyata memuat dua arsip:

| Arsip terlihat | Ukuran yang ditampilkan |
|---|---:|
| `TCP_Optimiser-2.4-16.zip` | 25,45 kB |
| `TCP_Optimiser-2.5-17.zip` | 396 kB |

Kedua file diperlihatkan sebagai arsip ZIP dalam kategori yang sama.
Pengguna menjelaskan bahwa **subfolder pada screenshot terdahulu
memang dipakai untuk menyimpan installer ZIP per modul**, dengan
kemungkinan lebih dari satu versi di satu folder. Ini mengoreksi
keraguan sebelumnya apakah subfolder berisi ZIP.

**Yang belum diperiksa:** isi/struktur ZIP itu sendiri, checksum,
keberadaan file installer pada **setiap** subfolder, versi arsip untuk
seluruh 16 modul yang sedang terpasang, serta apakah arsip sudah
disalin ke media eksternal. Jangan menganggap arsip ini merupakan
16 modul yang aktif: inventaris runtime/disk tetap sumber berbeda.

Catatan teknis: contoh kategori TCP Optimizer adalah **koleksi
installer**, bukan bukti bahwa modul TCP Optimizer terpasang atau
perlu diaktifkan sekarang. Tidak ada perubahan rencana jaringan
atau tindakan terhadap kernel.

**Kesimpulan:** strategi pemulihan berbasis ZIP cocok dengan kebiasaan
arsip pengguna. Pertahankan pengelompokan yang ada dan hindari
pengarsipan penuh `/data/adb` yang tidak diperlukan.

