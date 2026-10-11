# Kebijakan dokumentasi Cogan Kernel

**Tujuan:** pekerjaan bisa dilanjutkan besok, bulan depan, atau oleh
kontributor lain tanpa mengulang tebakan maupun kehilangan konteks.

## Kapan harus mendokumentasikan?

Dokumentasikan ketika melakukan perubahan source, workflow, pilihan
fitur, konfigurasi root, keputusan keselamatan, uji, kegagalan,
perbaikan, pengamatan langsung di HP, migrasi repository, atau rilis.

**Aturan untuk pengembangan berikutnya:**
1. Sebelum bekerja: baca [PROJECT_STATUS.md](PROJECT_STATUS.md),
   [DECISIONS.md](DECISIONS.md), dan [INCIDENTS.md](INCIDENTS.md).
2. Catat perubahan dan hasilnya pada [WORKLOG.md](WORKLOG.md): tanggal,
   tujuan, repo/cabang/commit, sebelum → sesudah, risiko, uji, tautan
   bukti, dan langkah berikutnya.
3. Perbarui [PROJECT_STATUS.md](PROJECT_STATUS.md) jika keadaan proyek
   berubah; perubahan arah ditambahkan ke [DECISIONS.md](DECISIONS.md).
4. Masalah / gagal / bootloop / kehilangan root: catat kronologi dan
   bukti dalam [INCIDENTS.md](INCIDENTS.md) tanpa mengarang penyebabnya.
5. Rilis/build: simpan workflow run, SHA kode workflow, SHA source kernel,
   SHA komponen root/SUSFS/NoMount, versi manager, nama dan SHA-256
   artefak, hasil verifikasi serta batas kompatibilitas perangkat.
6. Dokumentasi hanya mencatat **apa yang benar-benar dilakukan**.
   Langkah yang direncanakan tidak boleh ditandai sebagai sudah selesai.
7. Hubungkan file dokumentasi dari [README.md](README.md) agar mudah
   ditemukan. Dokumen lama tetap disimpan; koreksi disertai bukti.

## Tingkat kepastian yang WAJIB ditulis

- **Terverifikasi:** dilihat langsung dari GitHub/artefak/checksum/log.
- **Dilaporkan perangkat/pengguna:** screenshot, aplikasi, output Termux;
  dapat terkena spoofing, bug, atau keterbatasan alat.
- **Inferensi:** penjelasan yang mungkin, perlu diuji.
- **Belum diketahui:** pertanyaan terbuka.
- **Tidak boleh:** klaim kernel cocok, partisi sehat, root pasti aman,
  atau flashing aman hanya karena nama versi/KMI sama.

## Pengamanan dan privasi

Jangan mengunggah ROM/partisi mentah, token, PAT, secret, sertifikat privat,
IMEI, nomor seri, fingerprint perangkat unik, data akun atau kunci.
Publikasikan *ringkasan teknis dan checksum* saja bila tidak sensitif.
Jangan menaruh keluaran seluruh `getprop` dan `dmesg` publik tanpa
menyaring informasi pribadi. Simpan backup asli di tempat terpisah.

**Tidak ada tindakan otomatis lintas waktu** hanya karena kebijakan ini
ditulis. Dokumentasi harus diperbarui setiap kali pekerjaan dilakukan.
Pull request ke `dev/rothko` akan memiliki template dan pemeriksaan
catatan kerja, tetapi push langsung atau pekerjaan di luar GitHub
tidak tercakup seluruhnya.

## Format standar catatan kerja

```md
### YYYY-MM-DD — Judul pekerjaan
- Tujuan:
- Kondisi sebelumnya:
- Tindakan:
- Hasil terverifikasi:
- Apa yang hanya dilaporkan/inferensi:
- Repo, branch, dan commit:
- Workflow run dan hasil:
- Artefak + SHA-256 (jika ada):
- Dampak pada root, partisi, modul, keamanan:
- Yang BELUM diuji:
- Rencana berikutnya:
```

## Bahasa dan kontribusi

Bahasa Indonesia sebagai dokumentasi utama; versi Inggris kemudian,
Mandarin dapat ditambahkan sebagai penghormatan kepada pengembang awal.
Terjemahan tidak boleh mengubah makna bukti atau status pengujian.
Lihat [template Pull Request](../.github/pull_request_template.md).
