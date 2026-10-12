# KSUN + SUSFS Rothko — HOLD / handoff

**Status: HOLD at owner's request (2026-10-12).** Do not resume KSUN source integration, change scripts/workflows, build, merge, release, or flash until the owner explicitly requests continuation.

## Scope
- Device: Xiaomi 14T Pro (Rothko), BSP 6.1.57, baseline `dev/rothko`.
- Integration branch: `feat/rothko-ksun-susfs-compat-audit`, Draft PR #9.
- Pinned KSUN: `pershoot/KernelSU-Next@3438d6aa431f96a23f9e625bec3d53ce1fb14161`.
- Official Simonpunk SUSFS: `gki-android14-6.1@5192aa2d33b381b58c1051532f9e1dfa5de6e8d3`.
- BakaSU + SUSFS + NoMount remains a separate, held track (PR #8). MAMA / upstream KSU held under issue #10.

## Completed and verified
- Official SUSFS clone and pinned source acquisition succeeded on Actions.
- Read-only `git apply --check --verbose` of official 6.1 patch against clean Rothko BSP failed with exit 6 in run 38236950368, job 114769847590.
- Five rejected patch targets mapped, with dedicated review docs:
  1. `fs/exec.c`: include context differs; official patch also inserts sucompat hooks into exec path.
  2. `fs/namei.c`: upstream references `lookup_one_qstr_excl`, absent from Rothko source; function/API layout mismatch.
  3. `fs/proc/base.c`: include context differs.
  4. `fs/proc/task_mmu.c`: `show_smap` control flow differs (vendor uses `smap_gather_stats`).
  5. `mm/memory.c`: upstream expects `trace/hooks/mm.h` include absent in Rothko source.
- Audit workflow script now logs the exact upstream diff for those five files: commit `66701240a101038af2b4d45718c8d48a79af7063`, run 38240823889; this run still fails expected patch applicability gate.
- Most recent commit `ea9acdcb3d7b1a36e7cccc33e6f590405697aefa` added read-only KSUN execve/SELinux symbol audit. Documentation Guard succeeded; source-audit run 38241854970 was in progress at last check, and job logs were temporarily unavailable. **Do not claim its result or compatibility without new evidence.**

## Remaining validation, only after explicit resume
1. Inspect the latest read-only symbol audit results and verify actual KSUN execve hook declarations/definitions and signature compatibility.
2. Compare SELinux hide and hook ownership across pinned KSUN, official SUSFS, and Rothko; reject duplicate hook paths.
3. Verify ARM64 `TIF_PROC_NO_SU` bit allocation and KMI/ABI/API dependencies.
4. Review full upstream diff hunks and author carefully reviewed Rothko-specific adaptations; no forced patch.
5. Run reproducible checks, then separately authorize build and device testing with recovery procedure. A passing build cannot guarantee no bootloop.

## Safety
No kernel source patch application, build, flash, release, or merge has been performed by this KSUN audit track. Keep PR #9 Draft. Existing GitHub Actions runs may complete independently; this HOLD does not retroactively cancel already-started jobs.
