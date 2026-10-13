# Rothko BSP — emergency recovery checkpoint (2026-10-14)

**Reason:** ChatGPT application displayed an error; owner requested an immediate, durable recovery point. This is a state snapshot, **not** authorization to build, merge, release, or flash.

## Verified GitHub position before this checkpoint
- Repository: https://github.com/cogan17/Xiomi-14t-pro
- Audit branch: `feat/rothko-ksun-susfs-compat-audit`
- Audit HEAD **before checkpoint commit**: `3a921e23ce13fa65ec6142d9225543be61386c77`
- Target branch `dev/rothko`: `adada6d0d839b9aeeeeb9885b2a5465abac5a04f`
- Draft PR #9: https://github.com/cogan17/Xiomi-14t-pro/pull/9 — open, `mergeable_state=dirty`; Git ancestry conflict not resolved.
- Operational issue #12: https://github.com/cogan17/Xiomi-14t-pro/issues/12 — open; existing blockers and green isolated CI evidence remain authoritative.
- Earlier emergency snapshot: `docs/ROTHKO_EMERGENCY_CHECKPOINT_20261014_0449.md`. Do not overwrite or duplicate its history.

## Most recent source-only changes preserved
- `038c207`: rollback on partial root-driver integration failure.
- `76f2503`: symlink failure rollback test.
- `3451c5f`: continue cleanup even if one rollback action fails, report incomplete rollback explicitly.
- `4fd8ecd`: test incomplete rollback error.
- `3a921e2`: correct failure-injection newline in test and remove unused variable.
- Files: `scripts/rothko_install_root_driver.py`, `tests/test_rothko_install_root_driver.py`.
- **Tests on latest installer changes have NOT been executed or shown green.** No claim of installer completion. Avoid repeated network/CI attempts without a different, justified validation path.

## Outstanding work, ordered
1. Installer source-only unit-test execution on exact audit HEAD; if unavailable, mark blocked and move on rather than repeating.
2. KSUN pin provenance: installer `KernelSU-Next/KernelSU-Next@02a9e1c5fb2c4fd8117429fe004136332788c1b6` versus audit `pershoot/KernelSU-Next@3438d6aa431f96a23f9e625bec3d53ce1fb14161` are **diverged**. No automatic SHA unification or transfer of audit claims.
3. PR #9 Git three-way ancestry conflicts: copied dev files do not fix ancestry. Do not merge into `dev/rothko`; preserve audit work.
4. KSUN credential G2/G5, SELinux and SU_SESSION FD ownership/revocation remain HOLD.
5. SUSFS pinned `simonpunk/susfs4ksu@5192aa2d33b381b58c1051532f9e1dfa5de6e8d3` full integration remains blocked; isolated green candidate checks are not full compatibility proof.
6. NoMount compatibility follows verified KSUN+SUSFS contracts. BakaSU work deferred by owner.

## Non-negotiable safety and efficiency
- **BUILD HOLD:** no device kernel compilation, boot/init_boot images, flashable artifacts, release, flashing, PR merge, force-push, or baseline rewrite.
- Source-only reading, focused tests and justified isolated candidate work allowed.
- No duplicate work; at most **two attempts of the same approach**, stop after success; do not rerun green CI reflexively.
- Only checkpoint at meaningful milestones or emergency; do not generate a checkpoint every `Lanjutkan`.
- Preserve prior successful work; no speculative pin changes.
- The owner resumes by typing **`Lanjutkan`**. First verify latest branch/PR state, then continue the highest actionable **unfinished** task.

This file records state at the moment of interruption. Its own commit will advance the audit HEAD beyond the pre-checkpoint SHA above.
