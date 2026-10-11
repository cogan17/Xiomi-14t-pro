# Ringkasan perubahan

Jelaskan *apa* yang berubah dan alasannya.

## Klasifikasi

- [ ] Source/kernel/driver/patch
- [ ] Workflow/CI/build
- [ ] Dokumentasi saja
- [ ] Pemeriksaan keamanan/perangkat
- [ ] Perbaikan insiden

## Kondisi sebelum dan sesudah

**Sebelum:** 

**Sesudah:** 

## Bukti teknis

- Repository/branch/commit:
- Workflow run dan kesimpulannya:
- Sumber patch, upstream commit serta SHA sumber:
- Perangkat/firmware/slot (jika relevan):
- Hasil pengujian nyata:
- Risiko, keterbatasan, dan yang BELUM diperiksa:

## Dokumentasi

- [ ] Ada entri bertanggal di `docs/WORKLOG.md` jika menyentuh
      source, build, CI, konfigurasi, keamanan atau perilaku perangkat.
- [ ] `docs/PROJECT_STATUS.md` diperbarui bila status berubah.
- [ ] `docs/DECISIONS.md` diperbarui bila ada keputusan arsitektur/fitur.
- [ ] `docs/INCIDENTS.md` diperbarui bila insiden ditemukan/berubah.
- [ ] Jika hanya dokumentasi, jelaskan dokumen mana yang diperbaiki.

## Keselamatan

- [ ] Tidak ada rahasia, PAT, token, IMEI, sertifikat privat, atau image
      partisi mentah yang ditambahkan ke repo.
- [ ] Tidak mengklaim kernel aman-flash tanpa uji kompatibilitas nyata.
- [ ] Tidak melewati validasi ABI/KMI/SUSFS/NoMount.
- [ ] Source dasar Xiaomi `bsp-rothko-u-oss` tetap tidak berubah.

> Catatan: template mengingatkan reviewer; checklist tidak dengan
> sendirinya membuktikan pengujian/keamanan.
