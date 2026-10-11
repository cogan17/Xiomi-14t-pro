# Tahap 6 — Audit kompatibilitas modul vendor (read-only)

Status: **BELUM TERBUKTI KOMPATIBEL, tidak boleh flash**.

## Bukti tersedia

- Arsip stock `OS3.0.301.0.WNNIDXM.zip`: identitas firmware `rothko`,
  kernel stock dalam `boot.img`: `6.1.138-android14-11`.
  Baca rincian dan checksum pada [ROTHKO_STOCK_FIRMWARE_AUDIT.md](ROTHKO_STOCK_FIRMWARE_AUDIT.md).
- Keluaran `uname -a` di HP menampilkan `6.1.170`, namun pengguna
  mengonfirmasi spoofing melalui SUSFS. **Jangan jadikan nilai ini sumber kebenaran**.
- Cogan GKI r7 memiliki artefak `6.1.177`, tetapi kesamaan kernel aktif
  dan kecocokan modul vendor belum diperiksa.
- Source Xiaomi mandiri punya `Makefile 6.1.57`.
- Modul vendor mungkin berada di `vendor_dlkm`, `vendor/lib/modules`,
  atau `odm_dlkm`; ZIP firmware yang diaudit tidak menyediakan image `vendor_dlkm`.

## Yang dilakukan berikutnya

Jalankan [scripts/collect_rothko_probe.sh](../scripts/collect_rothko_probe.sh)
di perangkat **setelah membaca isinya**. Skrip hanya:
- menampilkan properti firmware dan slot aktif,
- mencatat lokasi simbolik partisi (tidak membaca/menulis blok partisi),
- menghitung file `.ko` dan mencoba membaca `vermagic` dari beberapa modul,
- menghitung modul yang tampak pada `/proc/modules`.

Cara menjalankan dari Termux (membutuhkan `curl` dan root):

```sh
curl -fL --proto '=https' --tlsv1.2 \
  https://raw.githubusercontent.com/cogan17/Xiomi-14t-pro/dev/rothko/scripts/collect_rothko_probe.sh \
  -o "$HOME/collect_rothko_probe.sh"
cat "$HOME/collect_rothko_probe.sh"
su -c "sh /data/data/com.termux/files/home/collect_rothko_probe.sh"
```

Perintah di atas hanya contoh. Bila direktori Termux berbeda,
salin skrip ke direktori yang sesuai. Jangan menjalankan skrip dari URL
langsung menggunakan pipe menuju shell.

## Batasan

- `modinfo` dan `strings` mungkin tidak tersedia: ketiadaan hasil bukan
  bukti bahwa modul cocok.
- Berkas .ko statis dan metadata `vermagic` **tidak cukup** untuk
  membuktikan kompatibilitas ABI/CRC simbol yang dibutuhkan.
- SUSFS dapat memengaruhi apa yang terbaca pengguna;
  data HP mesti divalidasi terhadap artefak boot dan sumber build.
- Status slot **Unbootable: Yes** yang terlihat pada screenshot Kernel Flasher
  khusus **Slot B** tidak boleh diabaikan. Skrip ini tidak mengubah statusnya.
- Tidak ada root patch, build, flash, reset slot, atau perubahan perangkat.

## Persyaratan sebelum build perangkat

1. Pastikan informasi slot aktif, firmware, dan inventaris modul vendor;
2. Bandingkan CRC simbol/vermagic dengan output build GKI yang benar;
3. Verifikasi sumber khusus perangkat, DT/DTBO, dan modul vendor;
4. Uji patch KSU/KSUN/BakaSU serta SUSFS/NoMount terpisah, tanpa
   mengecualikan pengaman ketidakcocokan;
5. Baru tentukan rencana build dan pemulihan untuk pengujian terbatas.

## Hasil nyata dari HP (12 Oktober 2026)

Sumber: keluaran `scripts/collect_rothko_probe.sh` yang dijalankan melalui
Termux dengan `su`. Angka-angka ini merekam **apa yang teramati**, bukan
hasil uji kesetaraan CRC simbol dan bukan izin untuk flashing.

| Properti | Hasil |
|---|---|
| `ro.product.device` | `rothko` |
| `ro.product.vendor.device` | `rothko` |
| `ro.build.version.release` | `16` |
| `ro.build.version.security_patch` | `2026-10-02` |
| `ro.vendor.build.version.security_patch` | Kosong |
| `ro.build.version.incremental` | `OS3.0.301.0.WNNIDXM` |
| `ro.boot.hardware` | `mt6989` |
| `ro.boot.slot_suffix` | `_a` |
| `bootctl get-current-slot` | Gagal: `Error getting bootctrl v1.0 module.` |
| Alias partisi `/dev/block/by-name` | `boot_a/b`, `init_boot_a/b`, `vendor_boot_a/b`, `dtbo_a/b` terdeteksi |
| File `.ko` regular `/vendor_dlkm/lib/modules` | `268` |
| File `.ko` regular `/vendor/lib/modules` | `0` |
| File `.ko` regular `/system_dlkm/lib/modules` | `60` |
| Jumlah baris `/proc/modules` | `519` |

Contoh `vermagic` **file** modul vendor:

```text
adsp-v2.ko     6.1.138-android14-11-ga418eeb69cb6 SMP preempt mod_unload modversions aarch64
apu_aov.ko     6.1.138-android14-11-ga418eeb69cb6 SMP preempt mod_unload modversions aarch64
apu_top.ko     6.1.138-android14-11-ga418eeb69cb6 SMP preempt mod_unload modversions aarch64
apusys.ko      6.1.138-android14-11-ga418eeb69cb6 SMP preempt mod_unload modversions aarch64
```

Contoh `vermagic` **file** modul system DLKM:

```text
6lowpan.ko     6.1.138-android14-11-g6ab8c9a86a33-ab14396278 SMP preempt mod_unload modversions aarch64
8021q.ko       6.1.138-android14-11-g6ab8c9a86a33-ab14396278 SMP preempt mod_unload modversions aarch64
aqc111.ko      6.1.138-android14-11-g6ab8c9a86a33-ab14396278 SMP preempt mod_unload modversions aarch64
asix.ko        6.1.138-android14-11-g6ab8c9a86a33-ab14396278 SMP preempt mod_unload modversions aarch64
```

Nilai `g6ab8c9a86a33-ab14396278` sesuai dengan versi tertanam pada
`boot.img` stock Rothko di arsip `WNNIDXM`. Perbedaan akhiran vendor
`ga418eeb69cb6` dan system `g6ab8c9a86a33` perlu diperiksa terhadap
asal build masing-masing; **belum** ada bukti CRC modul cocok dengan
kernel hasil build GKI Cogan `6.1.177`.

**Batasan yang penting:** `vermagic` dari file di disk bukan identitas
kernel yang sedang berjalan. Perhitungan 519 baris `/proc/modules` juga
tidak harus sama dengan jumlah berkas `.ko` di dua direktori yang diperiksa.
Slot aktif `_a` dilaporkan properti boot, tetapi `bootctl` tidak dapat
membaca status kontrol slot. Tidak ditemukan alias `vendor_dlkm` di path
partisi yang dicetak; `vendor_dlkm` dapat berupa partisi logis atau mount
tersendiri sehingga ketiadaan alias **bukan** bukti tidak ada partisi.

### Gerbang selanjutnya (BELUM LULUS)

1. Kumpulkan metadata modul (simbol `__versions` / CRC bila tersedia)
   dan asal build yang benar pada kernel Cogan r7.
2. Verifikasi konfigurasi dan KMI/ABI yang dipakai root, SUSFS, NoMount dan
   modul MediaTek untuk firmware Rothko tertentu.
3. Jangan melakukan `insmod`, `modprobe`, `bootctl set-active-boot-slot`,
   flashing, atau mematikan validasi `CONFIG_MODVERSIONS` sebagai jalan pintas.

**Status akhir: audit inventaris berhasil, kompatibilitas ABI belum terbukti.**

## Bukti tambahan: BakaSU Manager + Kernel Flasher Slot A (12 Oktober 2026)

Dua screenshot pengguna memberikan bukti tambahan yang lebih spesifik
dibanding `uname` yang di-spoof SUSFS. Angka yang dilaporkan aplikasi
dicatat sebagai **observasi dari antarmuka**, bukan pengujian ABI atau
verifikasi kriptografis partisi.

| Data | Observasi |
|---|---|
| Perangkat pada BakaSU | Xiaomi 14T Pro |
| BakaSU kernel driver | `v4.2.0-rc3-5b76b884 (35222/5)` |
| BakaSU manager | `v4.2.0-rc3 (35222/5)` |
| SUSFS pada manager | `v2.3.0` |
| SELinux | `Enforcing` |
| Kernel Flasher | `Slot A [Active]` |
| Slot A kernel version field | `6.1.177-android14-11-Cogan` |
| Slot A build timestamp | `2026-10-10 03:36:04 UTC` |
| Slot A boot SHA1 prefix | `82d969f0` (hanya prefiks yang ditampilkan) |
| Slot A boot/init_boot format | `lz4_legacy` |
| Slot A Vendor DLKM | `Exists, Mounted` |
| Slot A Unbootable | `No` |
| Slot A Successful | `Yes` |

### Interpretasi yang diperbolehkan

- **Slot A ditandai aktif, bootable, dan sukses**, serta Kernel Flasher
  mengidentifikasi image kernel sebagai `6.1.177-android14-11-Cogan`.
  Ini menguatkan bahwa kernel Cogan terpasang pada Slot A, tetapi belum
  memastikan bahwa byte dari image Slot A identik dengan aset r7 tertentu.
- Kode versi BakaSU Manager dan driver **sama** (`35222/5`),
  sementara SUSFS melaporkan `v2.3.0`. Ini bukti konsistensi
  versi yang tertera, bukan verifikasi keseluruhan root/NoMount.
- Kernel vendor/system DLKM yang tersimpan menggunakan `vermagic`
  `6.1.138-android14-11-...`; ini **tidak otomatis berarti modul gagal
  dimuat** pada GKI 6.1.177. Diperlukan audit simbol/CRC dan log
  pemuatan untuk menentukan kompatibilitas sebenarnya.
- Slot B sebelumnya dilaporkan `Unbootable: Yes`, `Successful: No`.
  Status tersebut bukan diagnosis kerusakan hardware, dan tidak ada
  hubungan kausal yang terbukti dengan `init_boot.img` model degas.
- **Isi `init_boot_a` saat ini belum diidentifikasi.** Kemiripan ramdisk
  stock `degas` dan `rothko` serta root yang berjalan tidak dapat
  memastikan apakah `init_boot_a` masih hasil patch dari model lain.
- Pada konfigurasi root GKI, root driver umumnya ada di `boot.img`.
  Mengganti `init_boot.img` dapat menghapus perubahan ramdisk/LKM bila
  masih digunakan; **tidak disarankan flashing tanpa audit mode root
  dan image aktif**.

### Larangan perubahan saat ini

Jangan mengubah slot, me-restore `init_boot` secara membabi buta,
mem-flash firmware degas, mengabaikan pengecekan ABI modul, atau
menyatakan kompatibilitas 6.1.177 berdasarkan tampilan aplikasi saja.
Simpan backup stock Rothko yang benar dan catatan build Cogan r7.
