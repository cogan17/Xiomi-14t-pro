# Audit `init_boot_a` aktif (hanya baca)

**Tujuan:** menjawab apakah image `init_boot` pada **Slot A yang aktif**
identik dengan firmware stock **Rothko**, identik dengan firmware stock
**Degas**, atau berbeda dari keduanya.

**Status:** skrip disiapkan, **belum dijalankan pada HP**. Tidak boleh
mengganti partisi/root/slot hanya dari hasil checksum.

## Referensi berasal dari ZIP yang sudah diaudit

| Stock firmware | Codename | SHA-256 `init_boot.img` (8 MiB) |
|---|---|---|
| `OS3.0.301.0.WNNIDXM.zip` | `rothko` | `4b25ce3f4a321b34aa5f84e7c8b0328065d7038c1a00b91fdcca7e0c17fe463f` |
| `OS3.0.301.0.WNEIDXM.zip` | `degas` | `951f096146157773abe4cbbd9b0dacbe9c2fa6400d4c438298353e5fb8a8bf04` |

Backup **Slot B** sudah mengandung `init_boot.img` yang identik dengan
stock `rothko`; ini **tidak** membuktikan isi **Slot A**.

## Skrip read-only yang disiapkan

[scripts/check_active_init_boot.sh](../scripts/check_active_init_boot.sh)

Skrip melakukan:

1. Membaca `ro.product.device`, `ro.boot.slot_suffix`,
   `ro.build.version.incremental`; menolak perangkat bukan Rothko
   atau slot aktif selain `_a`.
2. Memastikan `/dev/block/by-name/init_boot_a` adalah perangkat blok.
3. Jika `blockdev` tersedia dan ukuran dapat dibaca, menolak ukuran
   yang tidak sama dengan **8.388.608 byte**.
4. Menghitung `sha256sum` langsung dari blok **untuk dibaca saja**:
   tidak ada salinan image, operasi `dd`, perubahan slot, flashing,
   perintah root manager ataupun modifikasi SUSFS.
5. Mengklasifikasi hanya tiga hasil di bawah.

| Klasifikasi | Penjelasan |
|---|---|
| `EXACT_ROTHKO_STOCK` | Sama byte-for-byte dengan ZIP stock Rothko bila ukuran partisi sesuai. |
| `EXACT_DEGAS_STOCK` | Sama dengan ZIP stock Degas. **Tidak boleh flash atau restore secara spontan.** |
| `DIFFERENT_FROM_BOTH_STOCK_IMAGES` | Berbeda dari keduanya; dapat dipatch root, tetapi belum tentu. Perlu inspeksi berikutnya. |

**Peringatan interpretasi:** ketidakcocokan hash **bukan** diagnosis
kerusakan; hash cocok juga **bukan** bukti bahwa kernel dan semua modul
ABI kompatibel. Jika `blockdev` tidak dapat memberi ukuran, hash tetap
dilaporkan tetapi kesimpulan kesetaraan harus ditinjau lebih hati-hati.

## Perintah Termux, setelah meninjau skrip

```sh
curl -fL --proto '=https' --tlsv1.2 \
  'https://raw.githubusercontent.com/cogan17/Xiomi-14t-pro/dev/rothko/scripts/check_active_init_boot.sh' \
  -o "$HOME/check_active_init_boot.sh"
cat "$HOME/check_active_init_boot.sh"
su -c "sh /data/data/com.termux/files/home/check_active_init_boot.sh"
```

Tidak ada operasi penulisan perangkat; dengan tetap memberi akses root,
**baca isi skrip dan pastikan URL** sebelum menjalankan.

## Belum diketahui / tindak lanjut

- Skrip belum dijalankan pada HP sehingga **hash `init_boot_a` aktif
  belum diketahui**.
- Jika hash berbeda dari kedua stock, perlu review image yang aktif secara
  read-only sebelum membuat klaim tentang LKM, AVB, atau penyebab Slot B
  unbootable. Jangan unggah image partisi pribadi secara publik.
- Seluruh modifikasi/restore tetap **ditahan**.

Lihat juga [backup Slot B](ROTHKO_SLOT_B_BACKUP_AUDIT.md),
[audit firmware](ROTHKO_STOCK_FIRMWARE_AUDIT.md), dan
[insiden](INCIDENTS.md).
