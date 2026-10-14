# Rothko BSP — Active recovery checkpoint

Updated: 2026-10-14. This is the **single current handoff index**, not a new deployment authorization. Earlier emergency/history checkpoints remain archival references; do not duplicate their audits.

## Owner rules — current development and continuation policy (2026-10-14)

These rules supersede older scope/next-action notes. Main work is **KSUN + SUSFS + NoMount**; BakaSU is deferred and its completed work is preserved. The last validated source milestone is [`8d10fc10`](https://github.com/cogan17/Xiomi-14t-pro/commit/8d10fc10eb3b0c5a28495c23404c134027e22044); this policy update creates no new technical checkpoint or runtime proof.

1. **No duplicate work.** Start from the existing checkpoint, candidate order and evidence. Finish or compose outstanding work before adding parallel alternatives. A green result is reused unless a relevant source/dependency changed or a concrete defect invalidates it. Independent reviewers must have distinct scope.
2. **Repeat only when necessary.** Stop immediately on success. Use one attempt when sufficient; at most two attempts/corrections with the same approach. Record the failure/cause and count when needed. At the limit, change strategy or record a precise blocker and proceed with an independent dependency; do not loop, weaken a gate or rerun merely to obtain a green result.
3. **Selective validation/CI.** Prefer the smallest relevant source-only check. CI/rerun is allowed when it answers a concrete unresolved question or validates a changed dependency; use existing workflows where suitable. No automatic whole-audit rerun after every edit. Report local evidence separately from CI and runtime. Workflow titles, job names and triggers must describe their real scope.
4. **Bounded backlog and selective checkpoints.** Keep the four priorities below as one queue. Every pending item needs its reason, dependency and next closing step. Difficult work may wait explicitly while independent work progresses. Update this existing checkpoint at a meaningful validated milestone, changed blocker or handoff; do not create a checkpoint file after every small change. Final reports still state commit, relevant validation, remaining blocker and next step.
5. **Maintain current metadata.** Tidy issue #12 and PR #9 when status, priorities or evidence materially change, not on every commit. Historical comments/commits/results are preserved; stale descriptions must not override this index. The owner can simply type **"Lanjutkan"** and work resumes from the first unresolved actionable item within these rules.
6. **BUILD HOLD remains binding.** Source-only candidates, conflict resolution and focused static tests are allowed. No kernel/device build, flashable image, flashing, release, PR merge, force push, history rewrite or weakening of integration gates. Runtime/build work needs separate explicit authorization.

| Priority | Current state | Next closing work |
| --- | --- | --- |
| **1 — KSUN** | Source-only precommit/borrow composition validated at `8d10fc10`; caller success handling, groups/seccomp, G2 rollback, teardown and SU_SESSION still blocked. | Compose existing groups/seccomp candidates, preserve preparation errors, and guard escape callers. Resolve the concrete lifecycle/security contracts before promoting integration. |
| **2 — SUSFS integration** | Existing passing proc/VFS/memory candidates and pinned source evidence retained; full BSP/KSUN companion integration, RCU, hook placement and teardown unresolved. | Resume the existing conflict matrix and source/Kconfig dependencies; integrate applicable pieces against the same pins without redoing green isolated audits or GitLab acquisition. Do independent conflict work when KSUN dependencies permit. |
| **3 — NoMount** | Full KSUN+SUSFS+NoMount integration not proven; historical NoMount compile experiment is now manual-only and its compile job is disabled under BUILD HOLD. | Continue source integration/compatibility after the relevant KSUN/SUSFS contracts; kernel compilation remains prohibited. |
| **4 — validation/workflow/issue/PR cleanup** | Current rules and status descriptions being aligned. NoMount title/automatic-build mismatch corrected. Duplicate root installer unit-test paths remain identified. | Consolidate duplicated installer CI when that integration path is next changed; preserve required checks and avoid a cleanup-only rerun. Maintain accurate workflow names and evidence-linked issue/PR status. |

## Current milestone — KSUN app-profile SELinux and namespace admission (2026-10-14)

Parent: `7421b71439d77b9355d257bdef58181b40f853b3`. **KSUN only; BakaSU excluded. Draft / BUILD HOLD.** This section supersedes older next-action notes.

- Added `patches/rothko-ksun-app-profile-selinux-status-candidate.patch`, limited to app-profile callers. Both profile and init `setup_selinux` failures abort prepared credentials before `commit_creds`; profile reference cleanup and exact SELinux error status are preserved. Existing SELinux API/status candidates remain unchanged, with no duplicate API hunks added.
- Added `patches/rothko-ksun-namespace-precommit-admission-candidate.patch`. Pure `ksu_mount_ns_precommit_status` accepts INHERITED, rejects GLOBAL/INDIVIDUAL with `-EOPNOTSUPP`, and rejects unknown modes with `-EINVAL`. App-profile checks immediately after acquiring its referenced profile, before UID/GID changes, SELinux transition, credential commit, seccomp or task-flag changes. Failure goes through existing profile-put/credential-abort cleanup. The postcommit namespace call is removed because only the no-op inherited mode is admitted.
- This intentionally blocks custom GLOBAL/INDIVIDUAL profile requests in this candidate. Default profile mode at pinned `allowlist.c:49` is INHERITED. Their implementation/borrow candidates are preserved for future transactional work; they are not silently enabled. Moving current namespace operations before commit is unsafe as a proposed transaction: successful setns followed by cwd failure, or unshare followed by failed remount, can leave namespace side effects with no rollback. The existing void namespace helpers still have these unresolved semantics.
- `tests/test_rothko_ksun_app_profile_precommit.py` extends the verified 16-stage G5 composition with the app-profile status candidate, then namespace admission. Local source-only validation passed all 18 forward/reverse checks/applications, 12 negative mutations, rejection of duplicate application for both new patches, and exact pinned-byte restoration of twelve source files at `pershoot/KernelSU-Next@3438d6aa431f96a23f9e625bec3d53ce1fb14161`. New hunks use standard contextual `git apply --check --whitespace=error`; only legacy G1 remains zero-context. No kernel build, separate green-audit rerun, or CI/runtime approval.
- The profile getter holds a kref on custom profiles; profile updates replace nodes rather than altering the selected referenced object. The admitted inherited mode performs no namespace mutation. This source reasoning is not runtime or module-lifetime proof.
- Remaining KSUN blockers: namespace transactions/rollback remain unsupported; some SU/ADB callers ignore escape status; late-load caller still ignores `escape_to_root_for_init` return and can continue boot-complete on errors. `set_cred_ucounts` failure currently loses its status; group setup errors and postcommit seccomp allocation failures need composition with existing candidates. G2 snapshot/replay/rollback, private owner/API boundaries, callback/proxy/module lifetime and SU_SESSION authorization remain HOLD.
- Next focused work: compose existing group/seccomp precommit candidates without API duplication, preserve nonzero status from credential preparation, and guard callers of root escape against continuing success paths after failure. Continue only source-level validation; build/flash/release/merge/force push remain prohibited.

## Prior milestone — KSUN G5 consumer/status composition (2026-10-14)

Parent: `a0da8f333ce87a0141a8359ab9f15d2aea1e0e5b`. Current user scope is **KSUN only; BakaSU excluded**. This section supersedes the older next-action notes below. Draft / BUILD HOLD remains unchanged.

- Added three separate candidates, preserving every existing patch: `g5-sucompat-borrow-composable` (same intended changes as the three old sucompat borrow candidates, regenerated with ordinary contextual hunks), `g5-module-rc-composable` (READY borrow plus synchronized loader/installer latches), and `g5-mount-ns-borrow` (both namespace credential uses). Full filenames have prefix `patches/rothko-ksun-` and suffix `-candidate.patch`.
- Corrected the historical caller inventory: the pin contains **seven direct shared overrides across five files plus one shared `dentry_open`**, including `infra/su_mount_ns.c:102,176`. The isolated composition removes raw owner access from all five consumer files. Owner/private-public API boundaries remain unfinished.
- `tests/test_rothko_ksun_g5_composition.py` is the exact 16-stage order/validation entry point: six-stage G1/G5 setup base -> boot cred status guard -> umount/allowlist/sucompat/module-RC/namespace borrowers -> G2 backup/status prerequisites -> second-stage policy status guard -> late-load local escalation gate. Invoke with a checkout at `pershoot/KernelSU-Next@3438d6aa431f96a23f9e625bec3d53ce1fb14161`. No patches are applied to the BSP or upstream input checkout.
- Local source-only validation passed all 16 forward checks/applications, 13 negative source mutations, all reverse checks/applications, and exact pinned-byte restoration of ten touched files. New patches use normal contextual `git apply --check --whitespace=error`; only the inherited zero-context G1 header needs `--unidiff-zero`. No recount/fuzz/whitespace relaxation, kernel build, or workflow rerun. This is not a CI/runtime success claim.
- Module-RC loader now acquires its mutex before every `loaded` observation and checks READY even on cached/no-custom-RC paths. Unavailable READY returns false without consuming `loaded`; installer checks that result before `rc_hooked`, hook disabling or proxy publication. Installer latch/proxy writes share a mutex. `true` means a READY-authorized one-attempt IO path completed, **not** successful IO: existing open/read failure semantics are preserved. Lock order is installer mutex -> loader mutex -> credential spinlock.
- Ordinary strict application exposed incomplete context in old sucompat candidates; the new composable candidate is byte-equivalent to their exact intended replacements. Old raw `get_cred`/pointer-domain module-RC alternatives are not composed. Existing `g2-second-stage-one-shot` currently conflicts with the new module-RC include context; it is preserved but excluded from this verified sequence. No safe retry/replay claim follows from the status guards.
- Concrete lifecycle evidence: non-SUSFS setup is reached through the syscall dispatcher -> exec event bridge -> KSUD helper without a KSUN spinlock/RCU critical section. Actual SUSFS BSP hook placement is absent, so its context is still unproven. Syscall hook removal does not wait for executing sleepable handlers; allowlist task-work has no module pin/cancel/drain; input-stop work and optional throne thread teardown are also incomplete. Existing proxy/buffer cleanup is not synchronized with these new mutexes. Teardown can still race installation after a successful borrow.
- Remaining KSUN blockers: namespace setup is void and runs after `commit_creds`, so borrow failure can skip namespace setup after SU credentials committed; fstat can advertise static RC bytes while read installation is pending; late-load errors still continue init/boot-complete and escape status is ignored; app-profile `setup_selinux` status is unchecked. G2 old-policy snapshot/replay/rollback, global/API bypass prevention, module/callback/proxy lifetime and SU_SESSION post-exec authorization remain HOLD.
- Next focused source-only work: close the namespace precommit/status contract and unchecked app-profile SELinux result without duplicating existing API hunks; then resolve G2 composition/replay and teardown/proxy quiescence. Do not repeat green audits. Build/flash/release/merge/force push remain prohibited.

## Prior milestone — G5 initial setup serialization (2026-10-14)

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
