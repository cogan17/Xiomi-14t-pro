# Audit `init_boot_a` aktif (hanya baca)

**Tujuan:** menjawab apakah image `init_boot` pada **Slot A yang aktif**
identik dengan firmware stock **Rothko**, identik dengan firmware stock
**Degas**, atau berbeda dari keduanya.

**Status diperbarui 2026-10-12:** skrip sudah dijalankan pada HP dan
membuktikan **init_boot_a aktif identik dengan stock Degas WNEIDXM**, bukan
stock Rothko WNNIDXM. Hasil ini **tidak** memberi izin mengganti
partisi/root/slot ataupun membuktikan adanya kerusakan.

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

- **Sudah terjawab:** checksum `init_boot_a` aktif identik dengan stock Degas
  (hasil Termux; ukuran partisi sudah dicek 8 MiB).
- **Belum diketahui:** bagaimana/kapan image Degas dipasang; apakah itu
  menyebabkan kegagalan sebelumnya; apakah ada komponen LKM/patch lain;
  dan penyebab status Slot B yang ditandai unbootable.
- Tidak ada bukti dari hash ini bahwa hardware atau Slot A rusak;
  Slot A saat ini tetap dilaporkan sukses boot dengan BakaSU.
- Seluruh modifikasi/restore tetap **ditahan**. Jangan unggah image partisi
  pribadi secara publik.

Lihat juga [backup Slot B](ROTHKO_SLOT_B_BACKUP_AUDIT.md),
[audit firmware](ROTHKO_STOCK_FIRMWARE_AUDIT.md), dan
[insiden](INCIDENTS.md).

## Hasil dari HP — 12 Oktober 2026 (bukti read-only)

Sumber: output Termux yang disalin langsung setelah pengguna menjalankan
`su -c 'sh /data/data/com.termux/files/home/check_active_init_boot.sh'`.
Skrip sebelumnya diperiksa dan diverifikasi sintaksnya oleh
[GitHub Actions #38168048874](https://github.com/cogan17/Xiomi-14t-pro/actions/runs/38168048874).

```text
device=rothko
slot=_a
firmware=OS3.0.301.0.WNNIDXM
partition_size_bytes=8388608
init_boot_a_sha256=951f096146157773abe4cbbd9b0dacbe9c2fa6400d4c438298353e5fb8a8bf04
classification=EXACT_DEGAS_STOCK
```

**Yang terbukti dengan checksum:** seluruh partisi `init_boot_a` berukuran
8 MiB yang dapat dibaca pada HP identik byte-per-byte dengan `init_boot.img`
stock **Xiaomi 14T (degas), OS3.0.301.0.WNEIDXM**, dari arsip yang
sudah diperiksa. Hash ini **tidak cocok** dengan stock
**Xiaomi 14T Pro (rothko), OS3.0.301.0.WNNIDXM**:
`4b25ce3f4a321b34aa5f84e7c8b0328065d7038c1a00b91fdcca7e0c17fe463f`.

**Kontras dengan Slot B:** backup `init_boot_b` yang diserahkan pengguna
**cocok dengan stock Rothko**, tetapi Slot B sebelumnya ditandai
`Unbootable: Yes`. Bukti ini tidak menerangkan penyebab status tersebut.

**Implikasi terbatas:** keberhasilan boot Slot A dan BakaSU dengan image
Degas terpasang dapat berkaitan dengan kemiripan isi ramdisk kedua
perangkat, tetapi tidak menjamin keamanan lintas-model atau mengesahkan
prosedur flashing Degas. Status root GKI/LKM campuran juga belum
dibuktikan hanya dengan hash. Jangan mem-flash `init_boot_a`, boot,
atau mengubah status slot tanpa backup image aktif dan rencana
pemulihan yang sudah diperiksa.

**Tidak dilakukan:** flashing, restore, penulisan partisi, penggantian
slot, pengubahan root, atau penonaktifan SUSFS.

## Koreksi riwayat pengguna: flashing ulang, LKM, lalu root GKI

**Keterangan pengguna (12 Oktober 2026):** insiden bootloop modul
yang sebelumnya diselamatkan dengan flash `boot.img` +
`init_boot.img` adalah **kejadian lama yang berbeda** dari
kondisi HP sekarang. Pengguna menjelaskan urutan/metode rooting
ketika perangkat di-flash ulang:

1. Metode **LKM** pada kernel biasa memerlukan `init_boot.img`
   untuk dipatch dengan root manager; image hasil patch dipasang
   ke partisi `init_boot`, kemudian Manager menampilkan LKM.
2. Metode **GKI / built-in**, seperti kernel patch dari WildKernel
   atau kernel Cogan yang kini terpasang, memperoleh dukungan root
   dari kernel custom, bukan hanya dari patch LKM `init_boot`.
3. Ini penjelasan metode yang digunakan pengguna, **bukan rekaman
   lengkap file bertanggal dan hash tiap instalasi**. Tidak
   diketahui apakah/pada tahap mana `init_boot_a` pernah
   ditimpa ulang ketika beralih dari LKM ke GKI.

**Kesesuaian teknis:** panduan instalasi resmi KernelSU menjelaskan
LKM mempatch ramdisk (`init_boot` pada perangkat Android modern),
sedangkan GKI mengganti kernel dalam `boot`. BakaSU merupakan
turunan KernelSU, tetapi ini **tidak otomatis membuktikan** semua
detail implementasi pada build pengguna. Referensi:
https://kernelsu.org/id_ID/guide/installation.html
https://github.com/Baka-SU/BakaSU

**Fakta biner tetap:** `init_boot_a` sekarang SHA-256 identik
dengan stock **Degas WNEIDXM** dan **berbeda dari stock Rothko
WNNIDXM**. Image yang pernah dipatch untuk LKM lazimnya akan
memiliki hash berbeda dari image stock asal, namun bukti ini
**tidak menentukan asal atau waktu terpasangnya Degas stock**.
Keberhasilan root Cogan GKI juga bukan bukti ramdisk Degas aman
untuk semua operasi/OTA.

**Gerbang keselamatan:** hanya inventaris/analisis read-only.
Tidak menghapus bekas LKM, tidak mengubah `init_boot_a`,
`boot_a`, slot, root manager atau modul berdasarkan dugaan.

