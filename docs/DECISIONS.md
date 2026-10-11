# Catatan keputusan Cogan Rothko

Setiap keputusan memiliki ID. **Status** dapat berupa `Diterapkan (dokumen/CI)`,
`Disepakati (rencana)`, atau `Menunggu bukti`. Tidak ada keputusan di sini
yang merupakan perintah untuk flashing.

| ID | Tanggal | Keputusan | Status dan alasan |
|---|---|---|---|
| D-001 | 2026-10-11 | Repo source `Xiomi-14t-pro` dibuat mandiri, bukan fork. Backup fork lama tetap tersedia. | Diterapkan. Pisahkan migrasi source dengan pengembangan. |
| D-002 | 2026-10-11 | Pertahankan `bsp-rothko-u-oss` sebagai baseline; semua eksperimen di `dev/rothko`. | Diterapkan. Mencegah perubahan tidak disengaja pada dasar source. |
| D-003 | 2026-10-12 | Root manager dapat dipilih: **KSU**, **KSUN**, **BakaSU**, atau **All** (3 varian terisolasi). | Pilihan CI diterapkan; integrasi/build nyata belum. Ketiganya menggunakan jalur driver `kernelsu`, sehingga bukan instalasi gabungan. |
| D-004 | 2026-10-12 | **Tidak menggunakan DroidSpaces dan NTSync** di proyek kernel Rothko. | Diterapkan untuk opsi kerja; tidak ada kebutuhan pengguna. |
| D-005 | 2026-10-12 | Nilai `uname 6.1.170` diperlakukan sebagai **spoofed oleh SUSFS**. | Diterapkan dalam audit; jangan gunakan sebagai identitas kernel nyata. |
| D-006 | 2026-10-12 | Bedakan source Xiaomi `6.1.57`, stock firmware `6.1.138`, dan kernel GKI Cogan `6.1.177`. | Diterapkan. Perbedaan source/versi membutuhkan validasi kode, ABI dan KMI. |
| D-007 | 2026-10-12 | Simpan bukti stock **Rothko WNNIDXM**; jangan gunakan image `degas WNEIDXM` untuk flashing Rothko. | Diterapkan sebagai aturan keselamatan. |
| D-008 | 2026-10-12 | **Jangan restore `init_boot_a` atau ubah slot hanya berdasarkan dugaan**. | Diterapkan sebagai pengamanan; Slot A berfungsi, Slot B belum pasti bootable. |
| D-009 | 2026-10-12 | Audit **read-only**, validasi module vermagic/CRC dan kompatibilitas root/SUSFS/NoMount sebelum build perangkat/flash. | Masih menunggu bukti; tidak menonaktifkan `CONFIG_MODVERSIONS`. |
| D-010 | 2026-10-12 | Setiap pekerjaan terdahulu dan selanjutnya perlu dokumentasi yang dapat ditelusuri. | Diterapkan dengan indeks, log, status, dan template kontribusi. |

## Format keputusan baru

```md
### D-XXX — Judul keputusan
- Tanggal:
- Latar belakang / masalah:
- Keputusan:
- Alternatif yang dipertimbangkan:
- Dampak / risiko:
- Status: rencana / diterapkan / dibatalkan / menunggu bukti
- Bukti: tautan commit, workflow, issue, log, atau checksum
- Koreksi atau revisi keputusan:
```

Jangan mengubah keputusan lama diam-diam. Saat keputusan dibatalkan,
catat keputusan pengganti dan alasannya dengan ID baru.
