# Audit backup Slot B — Xiaomi 14T Pro (rothko)

**Tanggal backup menurut `backup.json`:** `2026-10-12--02-02`  
**Metode:** pemeriksaan lokal, *read-only*, terhadap backup Kernel Flasher dan
arsip firmware `OS3.0.301.0.WNNIDXM.zip` yang diberikan pengguna.  
**Tujuan:** menyimpan bukti agar image `degas` dan `rothko` tidak pernah tertukar.

> **Bukan instruksi flashing atau jaminan bahwa Slot B dapat di-boot.**
> Tidak dilakukan perubahan partisi, pergantian slot, atau reset root.

## Input backup yang diperiksa

- `backup.json` (`type: raw`, `hashAlgorithm: SHA-256`)
- `boot.img`, `init_boot.img`, `vendor_boot.img`, `dtbo.img`,
  `vbmeta.img`.

Metadata backup melaporkan kernel:

```text
6.1.138-android14-11-g6ab8c9a86a33-ab14396278
#1 SMP PREEMPT Wed Nov 5 15:47:39 UTC 2025
```

Kernel Flasher pernah menampilkan **Slot B Unbootable: Yes,
Successful: No**. Status ini adalah informasi kontrol slot dan **tidak
sendirinya membuktikan kerusakan hardware** atau bahwa kelima image tidak
dapat dibaca.

## Pemeriksaan checksum berkas yang benar-benar diunggah

SHA-256 dari kelima file backup dihitung ulang; seluruhnya **persis sama**
dengan daftar `hashes` di `backup.json`.

| File backup | SHA-256 |
|---|---|
| `boot.img` | `d8fa7c0baa2de9d6a5590c6ad2515b52fd04a32d8b2f49055a44f8864b9de4c2` |
| `init_boot.img` | `4b25ce3f4a321b34aa5f84e7c8b0328065d7038c1a00b91fdcca7e0c17fe463f` |
| `vendor_boot.img` | `087e76586bb981bbd1f37334f68707bac1f3b81d9a88caa452a9433feb76a384` |
| `dtbo.img` | `47954740b3e890e0414cc5e5fc0f495c9750fe117d81f3607171d6b65c5eaff7` |
| `vbmeta.img` | `bfe79b5ba411e927943b8b918d802dd02ed751da384d4d7752e7e6b19c32b526` |

## Byte-level comparison against WNNIDXM stock ZIP

| Partisi | Hasil |
|---|---|
| `boot.img` | **Byte-for-byte identical** with stock ZIP (`67,108,864` B) |
| `init_boot.img` | **Byte-for-byte identical** with stock ZIP (`8,388,608` B) |
| `vendor_boot.img` | **Byte-for-byte identical** with stock ZIP (`67,108,864` B) |
| `vbmeta.img` | Stock ZIP's first `12,288` bytes match the raw `8,388,608`-byte backup; every remaining byte is `0x00`. Whole-file hashes differ because sizes differ. |
| `dtbo.img` | Full uploaded backup hash matches `backup.json`, but stock ZIP contains **no `dtbo.img`**, so content equality to firmware stock **cannot be established**. |

**Key finding:** The backed-up Slot B `init_boot.img` is identical to
the `rothko` stock `init_boot.img` from the matching
`OS3.0.301.0.WNNIDXM.zip`, **not** the alternate `degas`
firmware archive.

This is proof of **backup content at the time it was collected**, not proof
of what previously resided in a slot, what caused any past boot failure, or
what resides in current **active** `init_boot_a`.

## Correlating Slot A (not part of this backup)

The user's separate **Kernel Flasher Slot A** screenshot shows:

- `Slot A [Active]`, `Unbootable: No`, `Successful: Yes`.
- Kernel version in image: `6.1.177-android14-11-Cogan`.
- `Vendor DLKM: Exists, Mounted`.
- BakaSU reports kernel-driver code `35222/5` and manager code
  `35222/5`, SUSFS `v2.3.0`.
- `uname` was spoofed via SUSFS to display `6.1.170`; do not use
  that as a real kernel identity.

The observed success of Slot A is separate from the status of Slot B.
The fact that the Slot B backup is mainly stock **does not establish
why Slot B is currently marked unbootable**. No action is indicated
to overwrite an active `init_boot_a` while root is working.

## Limits and safe next steps

1. Keep the original Rothko firmware ZIP and raw Slot B backup in a
   separate, untampered location; verify their checksums before any
   future recovery use.
2. Do not use any `degas` partition images on `rothko`.
3. Avoid `bootctl` slot changes, `flash`, `restore`, and
   `Unmount Vendor DLKM` during this audit.
4. The **active** `init_boot_a` image was **not supplied or compared**.
   Determining if it still contains a custom/degas-patched ramdisk would
   require separate, explicitly read-only verification of the current
   slot; do not replace it merely to test a hypothesis.
5. Kernel module ABI, CRC symbol compatibility with GKI 6.1.177, and
   flash safety are **not** established by stock backup matching.
6. No raw partition images or private device data have been uploaded
   to GitHub—only metadata and checksums in this report.

Related:
- [Stock firmware audit](ROTHKO_STOCK_FIRMWARE_AUDIT.md)
- [Vendor ABI audit](ROTHKO_VENDOR_ABI_AUDIT.md)
- [Kernel lineage inventory](ROTHKO_LINEAGE.json)
