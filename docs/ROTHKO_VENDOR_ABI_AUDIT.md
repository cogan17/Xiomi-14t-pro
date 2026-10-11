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
