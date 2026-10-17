# rothko-engine — petunjuk untuk Claude

- Branch ini adalah **mesin build kernel rothko milik `cogan17/Xiomi-14t-pro`** (lihat `ENGINE.md`), bukan repo Cogan. Pengembangan rothko tidak boleh mengganggu repo Cogan (keputusan owner 2026-10-17, D-021).
- Dokumen kerja rothko ada di branch `dev/rothko`:
  - `docs/WORKLOG.md`;
  - `docs/DECISIONS.md`;
  - `docs/ROTHKO_GKI_BUILD.md`.

  `docs/WORK-AGREEMENT.md` di branch ini adalah salinan Cogan saat disalin (sejarah). Jangan dipakai sebagai peta kerja.
- Alur perubahan:
  1. PR ke `rothko-engine` (test di `validate.yml` harus hijau).
  2. PR ke `dev/rothko` untuk menaikkan `ENGINE_COMMIT` di `rothko/engine.lock`, disertai entri WORKLOG.
- Perbaikan dari Cogan disalin dengan `git cherry-pick`, bukan merge.
- Aturan owner tetap berlaku:
  - checkpoint berarti berhenti total sampai owner meminta lanjut;
  - run workflow, rilis dan flash hanya oleh owner, kecuali owner meminta secara eksplisit;
  - kompatibel dulu, flash belakangan;
  - bahasa Indonesia.
