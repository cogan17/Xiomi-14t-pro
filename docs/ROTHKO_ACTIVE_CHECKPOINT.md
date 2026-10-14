# Rothko BSP — Active recovery checkpoint

Updated: 2026-10-14. This is the **single current handoff index**, not a new deployment authorization. Earlier emergency/history checkpoints remain archival references; do not duplicate their audits.

## Current milestone — G5 initial setup serialization (2026-10-14)

Parent branch HEAD verified: `dd98db16d49db128944e953838b429cb1705281f`.
Older progress/next-action sections below are historical; this milestone supersedes their G5 setup instructions.

- Added separate source-only candidate `patches/rothko-ksun-g5-initial-setup-serialization-candidate.patch`; existing passing patches are preserved unchanged. Apply after G1 SELinux return contract -> shared cred status -> G5 cred borrow API -> READY repeat setup guard -> SELinux READY publication, against `pershoot/KernelSU-Next@3438d6aa431f96a23f9e625bec3d53ce1fb14161`.
- Public `setup_ksu_cred()` now holds a statically initialized mutex across status check, credential mutation, domain verification and publication. The internal domain helper has one call site, inside that wrapper. A second setup waits and then sees READY without mutating the published credential. Failure releases the mutex without publication; a later serialized retry remains possible (policy rollback is not proven).
- `ksu_unpublish_cred()` uses the same mutex before the existing spinlock, draining setup before setting STOPPING. It moves to the beginning of `kernelsu_exit()`, before teardown dismantles dependencies. A queued setup after STOPPING returns `-ESHUTDOWN` before touching the owner. Borrow/get remains under the spinlock; no sleepable operation occurs under it. Existing borrowed references retain their own credential reference after owner release, but this does not prove callback/module-code quiescence.
- Lifetime reasoning: setup wins mutex -> publish -> teardown drains and closes borrowing; teardown wins -> STOPPING -> setup denied; two initial setups -> one mutates, second returns READY status. Static locks support normal builtin initialization and a fresh module load; same-image repeated init after STOPPING is deliberately not re-enabled. No runtime/module unload approval follows.
- Validation: `python tests/test_rothko_ksun_g5_setup_serialization.py /path/to/pinned/KernelSU-Next` passed six sequential `git apply --check --whitespace=error` / apply stages, seven negative source mutations, reverse checks, and exact pinned-byte restoration of all four touched source files. Legacy G1 header is zero-context, requiring `--unidiff-zero` for that patch only; no recount, reject, whitespace relaxation, kernel build or workflow rerun. New candidate uses ordinary contextual hunks. Windows temporary Git checkout explicitly disables CRLF conversion for byte validation.
- Remaining blockers: this sequence is isolated and does not apply all caller/late-load guards. Pinned init/boot-stage callers ignore `setup_ksu_cred()` status and app_profile callers ignore the new `setup_selinux()` status; existing separate candidates must be composed and checked before integration. The mutable global and direct consumers remain in this isolated tree. External publication bypass prevention, full caller migration/composition, sleepable hook-context validation, callback/workqueue/module quiescence, policy rollback and runtime locking remain unproven. SU_SESSION FD, SUSFS/RCU, compile/link/ABI/KMI and NoMount blockers remain unchanged.
- Next: focused composition of existing consumer/status candidates with this lifecycle candidate, and explicit hook-context/quiescence verification. Do not repeat already-green SUSFS audits or invent a runtime-success claim. PR #9 remains Draft; **BUILD HOLD** remains in effect.

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

## 2026-10-14 pause handoff — G5 progress and immediate blocker

- All six direct shared-credential caller sites now have isolated borrow candidates: kernel_umount, allowlist, module-rc, and sucompat faccessat/stat/execve. Source-text hunk checks passed individually; the three sucompat patches passed sequential structural application. None is wired, compiled, or runtime-proven.
- G1 status, G5 borrow API, and READY publication candidates passed sequential structural matching (3 + 4 + 1 hunks), **but the pinned upstream setup_selinux() returns void while G1 expects int**.
- New prerequisite candidate: `patches/rothko-ksun-g1-selinux-return-contract-candidate.patch` (commit `0bf454ef`, header correction `882e0dac`). It changes setup_selinux() to return error status. **Must test sequential application of this prerequisite before G1/G5 and inspect other callers**.
- Outstanding blockers: repeated setup can mutate a published READY cred; module-rc static loaded flag has no concurrency synchronization; teardown quiescence, SU_SESSION FD and SUSFS integration remain unproven.
- **Next action on "Lanjutkan":** verify prerequisite -> G1 -> G5 API -> READY publication sequentially, then resolve actual return-signature/caller and READY lifecycle issues. Avoid repeated inventories.
- This pause does not change BUILD HOLD or Draft PR #9; no build, flash, release, or merge is authorized. Prior passing work must be preserved.

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
