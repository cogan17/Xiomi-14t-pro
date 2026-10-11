# Riwayat pengembangan Cogan Kernel Rothko

**Rentang catatan:** 9–12 Oktober 2026. Disusun dari riwayat percakapan
pengembangan, GitHub API, keluaran Termux, screenshot Kernel Flasher/BakaSU,
serta audit berkas firmware. **Bukan** sejarah seluruh upstream Xiaomi.

| Periode | Kegiatan dan hasil | Bukti |
|---|---|---|
| 9–10 Okt | Pengembangan terpisah GKI Cogan BakaSU/SUSFS, opsi kernel 6.1.177, NoMount, paket AnyKernel3. | [Repo GKI Cogan](https://github.com/cogan17/GKI_BakaSU_SUSFS) |
| 10 Okt | GKI Cogan **r7** sukses pada GitHub Actions, versi job `6.1.177-android14-lts-r7-BakaSU`; rilis pra-rilis dengan ZIP AnyKernel3. Tag menunjuk commit workflow `93474213af4cb702dc96d2c95d130948293427d9`. | [Run 38020806221](https://github.com/cogan17/GKI_BakaSU_SUSFS/actions/runs/38020806221), [rilis r7](https://github.com/cogan17/GKI_BakaSU_SUSFS/releases/tag/BakaSU-run-38020806221) |
| 11 Okt | Mulai proyek **source Rothko mandiri**; backup fork `cogan17/14t-pro-fork-backup` disimpan, repo non-fork `cogan17/Xiomi-14t-pro` dibuat. | [Repository Rothko](https://github.com/cogan17/Xiomi-14t-pro) |
| 11–12 Okt | Migrasi sejarah Git Xiaomi dengan workflow bertahap; run final **sukses**. Source `bsp-rothko-u-oss` di commit `924d8eb314b764a92dc7d8610def9239f0db566c`; cabang pengembangan `dev/rothko` dibuat terpisah. PAT migrasi kemudian dihapus oleh pemilik (dari screenshot). | [Run 38159102600](https://github.com/cogan17/Xiomi-14t-pro/actions/runs/38159102600) |
| 12 Okt | Dibuat pilihan **KSU, KSUN, BakaSU, All** (matrix terpisah) tanpa DroidSpaces/NTSync. Workflow masih **preview, bukan build**. | [Commit bacb0ed4](https://github.com/cogan17/Xiomi-14t-pro/commit/bacb0ed4ed6463c8c4227d325fdc18bd79d84278) |
| 12 Okt | Audit statis root, source, dan identitas kernel lulus CI. Ditemukan Makefile Xiaomi `6.1.57` berbeda dari target GKI Cogan `6.1.177`. | [Audit root](ROTHKO_ROOT_SOURCE_AUDIT.md), [lineage](ROTHKO_LINEAGE.json) |
| 12 Okt | Terungkap angka `uname 6.1.170` berasal dari spoofing SUSFS; versi aktif harus diverifikasi dari sumber yang lebih kuat. | [Audit vendor](ROTHKO_VENDOR_ABI_AUDIT.md) |
| 12 Okt | Arsip awal `OS3.0.301.0.WNEIDXM` ternyata untuk **Xiaomi 14T/degas**; arsip pengganti `OS3.0.301.0.WNNIDXM` cocok identitas **Xiaomi 14T Pro/rothko**. Kernel stock dalam `boot.img`: `6.1.138-android14-11`. | [Audit firmware](ROTHKO_STOCK_FIRMWARE_AUDIT.md) |
| 12 Okt | Termux melaporkan 268 modul vendor, 60 system DLKM; contoh `vermagic` modul stock 6.1.138 meski image Slot A menampilkan 6.1.177. | [Audit ABI](ROTHKO_VENDOR_ABI_AUDIT.md) |
| 12 Okt | Screenshot BakaSU dan Kernel Flasher memperlihatkan Slot A **Active / Successful** dan kode manager-driver `35222/5` sepadan; Slot B bertanda Unbootable. | [Audit ABI](ROTHKO_VENDOR_ABI_AUDIT.md) |
| 12 Okt | Backup mentah Slot B diperiksa: checksum lima image cocok dengan `backup.json`. `boot`, `init_boot`, `vendor_boot` identik dengan firmware stock Rothko; `dtbo` belum dapat dibandingkan. | [Audit backup Slot B](ROTHKO_SLOT_B_BACKUP_AUDIT.md) |

## Pelajaran teknis dari masalah sebelumnya

- Proyek source Xiaomi dan proyek GKI adalah **dua basis source berbeda**;
  angka patch tidak bisa ditempelkan begitu saja.
- Lolos CI dan sukses boot tidak otomatis membuktikan ABI modul vendor cocok.
- Kemiripan `init_boot.img` model degas/rothko dapat menjelaskan keberhasilan
  *patching LKM*, tetapi **tidak membuktikan aman untuk flashing lintas model**.
- Status Slot B `Unbootable` tidak memiliki penyebab pasti dari bukti saat ini.
- Diskusi dengan pengembang WildKernel **fatalcoder** tentang flashing
  `boot/init_boot` dan AK3 adalah konteks yang dilaporkan pengguna,
  **bukan bukti teknis bahwa prosedur tersebut cocok untuk firmware ini**.

## Kelanjutan riwayat

Untuk setiap pekerjaan baru, tambahkan entri bertanggal di
[WORKLOG.md](WORKLOG.md), perbarui [PROJECT_STATUS.md](PROJECT_STATUS.md),
dan catat pilihan yang mengubah arah proyek dalam [DECISIONS.md](DECISIONS.md).
Jangan menimpa atau menghapus fakta lampau; jika ada koreksi, tambahkan
referensi revisi.
