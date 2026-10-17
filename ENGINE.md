# Mesin build kernel rothko (salinan Cogan)

Branch `rothko-engine` adalah **mesin build kernel Xiaomi 14T Pro (rothko)** milik repo `cogan17/Xiomi-14t-pro`. Keputusan owner 2026-10-17 (D-021): mesin rothko berdiri sendiri di repo ini supaya perkembangan repo Cogan tidak terganggu.

- **Asal:** salinan [cogan17/Cogan](https://github.com/cogan17/Cogan) pada commit `d9cbc9f` (Cogan PR #87), lengkap dengan sejarah commit-nya. Mesin inilah yang menghasilkan run CI hijau Xiomi 38934173981 (percobaan 2, GKID 6.1.177) dan 38970833229 (kernel bawaan 6.1.138).
- **Dipakai oleh:** workflow *Cogan Rothko Kernel Builder* (branch default), lewat `rothko/engine.lock` di `dev/rothko` (`ENGINE_REPO=cogan17/Xiomi-14t-pro`, `ENGINE_COMMIT=<commit branch ini>`).
- **Isi khusus rothko:**
  - `TARGET_DEVICE=rothko`;
  - sumber kernel bawaan `KERNEL_SOURCE=stock` (ACK 6.1.138);
  - gate KMI `scripts/kmi_compat.py` dengan acuan BSP + kernel bawaan + GKI;
  - patch `kernel-patches/susfs/6.1-v2/*/stock-6.1.138/`.

  Semua dikembangkan **hanya di sini**, lewat PR ke `rothko-engine`. `validate.yml` menguji setiap PR.
- **Menyalin perbaikan dari Cogan:** Cogan tetap jadi contoh mesin GKI umum. Perbaikan umum dari Cogan disalin dengan `git cherry-pick` per commit, **bukan** `git merge`: sejak pemisahan, Cogan menghapus kode rothko, dan merge akan ikut menghapusnya di sini. Contoh:

  ```bash
  git remote add cogan https://github.com/cogan17/Cogan
  git fetch cogan dev
  git cherry-pick <commit>
  ```

  Setelah itu buka PR ke `rothko-engine`, lalu naikkan `ENGINE_COMMIT` di `dev/rothko`.
- **Dokumen kerja rothko** (WORKLOG, DECISIONS, ROTHKO_GKI_BUILD) ada di branch `dev/rothko`. `README.md`, `docs/WORK-AGREEMENT.md` dan dokumen Cogan lain di branch ini adalah salinan saat disalin (sejarah) dan tidak diperbarui di sini.
- **Kredit:**
  - Cogan (cogan17);
  - GKID / GKI-Duchamp-6.1 dan AK3-GKID (Ahmed Al-Nassif);
  - Android Common Kernel (Google);
  - KernelSU Next, BakaSU, SUSFS (simonpunk), NoMount (maxsteeel), Baseband Guard (vc-teahouse);
  - BBRv3 (Google BBR team).

## English

`rothko-engine` is the Xiaomi 14T Pro (rothko) kernel build engine of this repository: a copy of cogan17/Cogan at `d9cbc9f` with its history. It is the engine of the green CI runs 38934173981 and 38970833229. The rothko builder workflow uses it through `rothko/engine.lock` on `dev/rothko`. Rothko-specific changes happen only here, via pull requests to this branch. Generic fixes from Cogan are cherry-picked, not merged.
