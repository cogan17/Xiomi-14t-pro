# Rothko BSP — recovery checkpoint (2026-10-14)

**Status: DRAFT / BUILD HOLD / RELEASE BLOCKED.** This document is a recovery marker, not evidence of a bootable kernel or permission to build, merge, release or flash.

## Owner direction (supersedes older priorities)

**Main path: KSUN + SUSFS + NoMount. BakaSU is deferred.** Preserve completed work, but do not schedule new BakaSU development. No redundant or duplicated work; one attempt when successful, at most two attempts using the same approach before switching strategy. Run CI only to answer a concrete question. Create checkpoints at meaningful milestones, not after every change. Tidy issues and PRs selectively. Owner may simply say **“Lanjutkan”** to continue within these boundaries.

## Where to resume

- Repository: `cogan17/Xiomi-14t-pro`.
- Working branch: `feat/rothko-ksun-susfs-compat-audit`; PR [#9](https://github.com/cogan17/Xiomi-14t-pro/pull/9) **Draft**. Do not merge into `dev/rothko`.
- Build/release blocker: [issue #12](https://github.com/cogan17/Xiomi-14t-pro/issues/12).
- Verified recent changes: [776ea97](https://github.com/cogan17/Xiomi-14t-pro/commit/776ea97011eaf1443eb19265adcd00c406e1cd6b) fixes fixed BSP anchor checkout; [92fbb8f](https://github.com/cogan17/Xiomi-14t-pro/commit/92fbb8fb354664b8e8e6f7c06c2ae58b30363bbc) records SUSFS CI triage; [c0d8f30](https://github.com/cogan17/Xiomi-14t-pro/commit/c0d8f30ede77804041376d76a790f1aff8a53e51) adds source-only G5 unsafe-borrow guard. This checkpoint commit will be newer.
- PR #9 ancestry conflict was already fixed in [fb282f8](https://github.com/cogan17/Xiomi-14t-pro/commit/fb282f88c3ab9b768f7ed678327b16da6494152c). Do not repeat.

## Priority 1 — KSUN credential lifecycle

G2/G5 remain **BLOCKED**. Existing candidate patches cover status checks, stage latching, and a partial borrowed reference; none proves synchronized publication/READY, lifetime-safe acquisition of `ksu_cred`, teardown, or all six `override_creds(ksu_cred)` consumers. The newly added `scripts/rothko_ksun_cred_candidate_guard.py` identifies the unsafe raw global `get_cred(ksu_cred)` pattern but is **not yet tested** or a full solution. SU_SESSION FD post-exec authorization, ownership and revocation remain separate blockers. Next technical work: implement and review one coherent lifetime synchronization design on pinned KSUN, migrate all consumers, then focused source-only checks; avoid duplicating earlier reviews.

## Priority 2 — SUSFS integration

Pinned Simonpunk SUSFS commit `5192aa2d33b381b58c1051532f9e1dfa5de6e8d3`, tree `b39cd4117178ce73d2973f7bcdae5c74defc8f68`. Pinned Rothko BSP baseline `b2d8b54a0d8bb002d32dda24e58d2b5d0423546b`. Isolated proc/memory candidate [38479754947](https://github.com/cogan17/Xiomi-14t-pro/actions/runs/38479754947), BSP anchors [38479754952](https://github.com/cogan17/Xiomi-14t-pro/actions/runs/38479754952), KSUN candidate audit [38479754954](https://github.com/cogan17/Xiomi-14t-pro/actions/runs/38479754954), and installer tests [38479754958](https://github.com/cogan17/Xiomi-14t-pro/actions/runs/38479754958) were green. Full SUSFS audit [38479755005](https://github.com/cogan17/Xiomi-14t-pro/actions/runs/38479755005) **failed**: provenance exited 14 for credential/FD semantics, while upstream patch context conflicts remain in `fs/exec.c`, `fs/namei.c`, `fs/proc/base.c`, `fs/proc/task_mmu.c`, `mm/memory.c` and KSUN companion patch. Do not misreport isolated green as full integration. See `docs/rothko-susfs-porting-conflicts.md`. Do not repeat already-successful candidates.

## Priority 3 — NoMount

Integrate and validate only after KSUN/SUSFS contracts are resolved. NoMount is not currently cleared for runtime use.

## Priority 4 — validation / workflow cleanup

**New finding from owner's screenshot:** GitHub Actions run title `[DRAFT / RELEASE BLOCKED] Rothko KSUN + SUSFS source-only candidates #7` contains completed `Integrate BakaSU source (NO FLASH)`, completed `Integrate KernelSU-Next source (NO FLASH)`, and running `Compile BakaSU-enabled ARM64 Image (NON-FLASHABLE)`. This is a genuine workflow title/job/priority mismatch. The screenshot does **not** prove the running job failed or completed. Identify the exact workflow file and its trigger before editing. Preserve BakaSU results; separate or disable its automatic experimental path from KSUN/SUSFS main work without deleting successful artifacts. Avoid triggering new builds. A direct workflow-list API attempt failed; no workflow fix has been committed.

## Explicit safety boundaries

- No kernel/device builds, boot/init_boot images, AK3 ZIP, release, flashing, force-push, history rewrite, or PR merge to `dev/rothko` while BUILD HOLD applies.
- Source-only analysis, narrowly scoped patches/tests, documentation and non-build workflow corrections are permitted.
- Do not unify diverged KSUN installer/audit pins automatically; document and review intentionally.
- BakaSU work deferred; do not discard earlier successes.
- Next `Lanjutkan`: resume unfinished G2/G5 technical implementation or the narrowly scoped workflow misrouting fix, not another generic audit or checkpoint.

Checkpoint records known status only; unverified runtime behavior is not claimed.
