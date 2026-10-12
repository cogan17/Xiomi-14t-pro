# Tahap 11 — Perlindungan BakaSU, SUSFS, NoMount dan seluruh modul

**Tanggal:** 12 Oktober 2026  
**Status:** rencana audit; skrip inventaris **belum dijalankan di HP**.  
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
- Pada screenshot lama BakaSU terdapat angka badge **16** pada tab
  modul. Ini **bukan** inventaris nama/versi/status modul saat ini.

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
