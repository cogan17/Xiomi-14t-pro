# Arsip internal KSU/Mama — tidak aktif

**Keputusan pemilik: 14 Oktober 2026.** Proyek KernelSU klasik (disebut **KSU/Mama**) ditutup dari alur kerja Cogan Rothko. Ini adalah arsip **di dalam** repository, BUKAN pengarsipan keseluruhan repository GitHub.

**Hanya dua root manager aktif: KSUN (KernelSU-Next) dan BakaSU.** Keduanya tetap varian terpisah. Pilihan historis KSU/Mama dan "All (KSU + KSUN + BakaSU)" tidak ditawarkan lagi di jalur aktif.

Jika suatu hari orang lain ingin melanjutkan pengembangan KSU/Mama, silakan **fork** [repository Cogan Rothko](https://github.com/cogan17/Xiomi-14t-pro) dan mengembangkan pada fork masing-masing.

## Jejak dan pemulihan historis

- Referensi sumber KSU/Mama (tidak aktif): [tiann/KernelSU](https://github.com/tiann/KernelSU).
- Commit sumber KSU historis: `f895b80a3aad79948ba8074f53cf8f65a314d576`.
- [Snapshot Git terakhir sebelum keputusan arsip, `dev/rothko@b2d8b54`](https://github.com/cogan17/Xiomi-14t-pro/tree/b2d8b54a0d8bb002d32dda24e58d2b5d0423546b). Di snapshot ini terdapat formulir, root-driver integration, matriks audit tiga root, dan tes asli. **Tidak ada history rewrite, force push, atau penghapusan commit.**
- [Catatan keputusan](../../DECISIONS.md): D-003 merupakan pilihan historis, digantikan D-016.

**Catatan penting:** Nama simbol kernel `CONFIG_KSU` dan folder `drivers/kernelsu` tetap diperlukan oleh KSUN/BakaSU; jangan menghapusnya hanya karena KSU/Mama diarsipkan.

Tidak ada build, release, flashing, atau bukti ABI/KMI dan runtime yang disetujui di sini. Status Rothko **BUILD HOLD** tetap berlaku.
