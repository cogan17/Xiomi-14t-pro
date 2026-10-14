# Rothko BSP — Active recovery checkpoint

Updated: 2026-10-14. This is the **single current handoff index**, not a new deployment authorization. Earlier emergency/history checkpoints remain archival references; do not duplicate their audits.

## Scope and hard limits

- Repository: `cogan17/Xiomi-14t-pro`; working branch: `feat/rothko-ksun-susfs-compat-audit`; target PR: [#9](https://github.com/cogan17/Xiomi-14t-pro/pull/9) **Draft**; [issue #12](https://github.com/cogan17/Xiomi-14t-pro/issues/12) **BUILD HOLD**.
- Source-only candidates, focused static tests and non-build CI permitted. **No device/kernel builds, boot/init_boot/AK3 flashable images, releases, flashing, PR merge into dev, force push or history rewrite.**
- Preserve existing passing candidates. No duplicate work; maximum two attempts per failed approach, then change approach. Do not rerun expensive checks without a new cause.
- Priority: **KSUN G2/G5 shared credential and SU_SESSION FD -> SUSFS integration -> NoMount -> final validation**. BakaSU postponed; do not modify it as part of this checkpoint.

## Confirmed progress (not deployment proof)

1. Pinned KSUN upstream: `pershoot/KernelSU-Next@3438d6aa431f96a23f9e625bec3d53ce1fb14161`. G1 SELinux shared-credential status candidate and isolated audit previously passed.
2. G5 API candidate: `patches/rothko-ksun-g5-cred-borrow-api-candidate.patch` defines synchronized borrow/return, READY gate and STOPPING teardown. Four hunks were structurally matched against pinned source; **not git-apply/compile/runtime verified**. Teardown now closes borrowing before `ksu_feature_exit()`: commit `358cea78e39f49c635cc81175420a57e3204193e`.
3. READY publication candidate: `patches/rothko-ksun-g5-selinux-ready-publication-candidate.patch` at `3e643a4`. **Not integrated**; repeated calls from second_stage/zygote may conflict with duplicate-READY rejection. Return-code redesign was discussed but **not committed**.
4. First of six direct `override_creds(ksu_cred)` sites staged: `patches/rothko-ksun-g5-kernel-umount-borrow-candidate.patch` at `6e0bd452ee3800f10e5d545ba893a9ed81a75812`. **Five sites remain** (three sucompat, one allowlist, one ksud_integration). Do not confuse candidate creation with runtime migration.
5. SUSFS isolated proc/memory, exact hunk, BSP anchor and source-only KSUN checks have green results. Full SUSFS conflicts, RCU lookup path, workqueue teardown, Kconfig/compile/link/ABI/KMI and post-exec hooks remain unresolved.
6. GitLab transport/source verification passed earlier; no reason to repeat absent a changed upstream dependency. NoMount integration not complete.

## Latest CI observation

At checkpoint creation, latest runs on `6e0bd452`: **SUCCESS** for SUSFS isolated proc/memory, SUSFS exact hunk comparison, KSUN independent candidate audit, root installer unit tests, SUSFS BSP anchors, documentation guard and KSUN root driver source integration (no build). **FAILURE** for `Rothko SUSFS source audit (read-only)`. This full-audit failure is a known blocker, **not** proof other isolated tests failed. CI status is a point-in-time observation; inspect new run IDs before asserting new results.

## Unresolved safety and compatibility blockers

- G5: publish only after verified SELinux setup; distinguish READY from STOPPING and handle legitimate repeated setup; migrate remaining five consumers; ensure teardown quiescence and no UAF; test patch order/application and failure paths.
- SU_SESSION FD: post-exec authorization, owner identity, lifecycle, fork/dup/close/revocation, failure handling not proven.
- SUSFS: complete patch conflicts and RCU semantics without losing passing non-RCU paths; full source audit failing; integration/runtime not proven.
- NoMount: version/contract and integration validation pending.

## Resume exactly here on user instruction “Lanjutkan”

1. Check latest branch/CI once; do not rerun already-green checks without a code change.
2. **Implement source changes**, not more inventory/checkpoint docs: resolve READY/STOPPING repeated-setup semantics and migrate next credential consumer in an isolated candidate; validate hunk context, then source-only tests.
3. Keep failed full SUSFS audit classified as expected blocking evidence until its concrete dependencies are resolved. Avoid masking failure or claiming release readiness.
4. Update this file **only when a meaningful milestone changes**, rather than creating another checkpoint. Maintain Draft and BUILD HOLD.

## Archival pointers

- [Emergency checkpoint](ROTHKO_EMERGENCY_CHECKPOINT_2026-10-14.md)
- [Priority checkpoint](ROTHKO_RECOVERY_CHECKPOINT_2026-10-14_PRIORITY_KSUN_SUSFS_NOMOUNT.md)
- [G5 credential contract](ROTHKO_KSUN_G5_CREDENTIAL_LIFETIME_CONTRACT.md)
- [G5 caller inventory](ROTHKO_KSUN_G5_CREDENTIAL_CALLER_INVENTORY.md)
