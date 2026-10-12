# HOLD — Rothko KSUN/SUSFS pending relevant Simonpunk readiness

Owner requested all active SUSFS integration work be saved and held on 2026-10-12. Do not resume, merge, build, release, or flash without explicit owner instruction after relevant official Simonpunk SUSFS updates are ready and independently checked.

Existing handoff: `docs/KSUN_HOLD_HANDOFF.md`. Draft PR #9 remains unmerged. Pinned KSUN `3438d6aa431f96a23f9e625bec3d53ce1fb14161`; official SUSFS `5192aa2d33b381b58c1051532f9e1dfa5de6e8d3`. Five rejected BSP patch files and execve/SELinux/TIF_PROC_NO_SU concerns remain unresolved. The read-only audit workflow may have completed independently; verify logs only after explicit resume. Do not assume successful integration.

BakaSU companion repository `cogan17/GKI_BakaSU_SUSFS` preserves main in backup branch `backup/cogan-main-before-upstream-sync-20261012`, with upstream NoMount not cherry-picked and Re-Kernel selective port deferred. MAMA/upstream KernelSU remains HOLD under issue #10.

Resume only on owner instruction, then check source/API/ABI/KMI, hook ownership, SELinux hide, patch applicability, and tests. No bootloop-free guarantees.
