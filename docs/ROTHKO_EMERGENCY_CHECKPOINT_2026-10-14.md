# Rothko BSP — EMERGENCY CHECKPOINT (2026-10-14)

> Emergency recovery record. Do not interpret this document as a release approval or a successful integration test.

## Immutable reference / recovery
- Repository: https://github.com/cogan17/Xiomi-14t-pro
- Working branch: `feat/rothko-ksun-susfs-compat-audit`
- Last source/patch revision before this checkpoint: `dd22612735b6c1215fa048a4622b16e4d13c451f`.
- Earlier recovery milestone: `bca2408f3e4f7f810142159c7c13e5de25efe05c`, documented in `docs/ROTHKO_RECOVERY_CHECKPOINT_2026-10-14_PRIORITY_KSUN_SUSFS_NOMOUNT.md`.
- PR #9: https://github.com/cogan17/Xiomi-14t-pro/pull/9 — KEEP DRAFT.
- Issue #12: https://github.com/cogan17/Xiomi-14t-pro/issues/12 — BUILD HOLD.

## Hard safety restrictions
- BUILD HOLD: no kernel/device build, boot/init_boot.img, AK3/ZIP, release, flashing, or merge of PR #9; no force-push/history rewrite.
- Preserve prior successful source changes, candidates, workflow corrections, and all BakaSU-related results. BakaSU is deferred, not deleted.
- Work source-only with selective checks. No redundant CI/build triggers. Stop repeating the same failed method after two attempts.
- Priorities: (1) KSUN G2/G5 shared credential security and SU_SESSION FD, (2) SUSFS full integration, (3) NoMount, (4) workflow/issues/PR cleanup.

## Most recent verified CI result — IMPORTANT
- `dd22612735b6c1215fa048a4622b16e4d13c451f` candidate audit runs:
  - https://github.com/cogan17/Xiomi-14t-pro/actions/runs/38487250026 — FAILURE
  - https://github.com/cogan17/Xiomi-14t-pro/actions/runs/38487245073 — FAILURE
- Failing step: `Verify isolated G1 helper candidate applicability (no kernel build)`.
- Log: `error: while searching for:` followed by `error: patch failed: kernel/selinux/selinux.c:159` and `patch does not apply`.
- Previous revisions failed with `corrupt patch ...:45`. The latest revision repaired the counted hunk header, but the context still does not match the pinned source. DO NOT report G2 as green or repeat manual hunk-count guesses.
- Pinned KSUN audit source: `pershoot/KernelSU-Next@3438d6aa431f96a23f9e625bec3d53ce1fb14161`.
- Current candidate: `patches/rothko-ksun-shared-cred-status-candidate.patch`. The candidate changes `setup_ksu_cred` to return a status; it is not a concurrency/lifetime solution.

## Resume exactly here
1. Fetch the full pinned `kernel/selinux/selinux.c` and `kernel/selinux/selinux.h` as well as the current candidate patch. Diagnose exact whitespace/context mismatch against the pinned source (not approximate line numbers).
2. Generate a deterministic unified diff from exact pinned file bytes and modified file bytes; verify applicability and reverse applicability. Only then commit the corrected patch. Do not launch a kernel build.
3. Review candidate-audit CI result; distinguish patch applicability from actual G2/G5 security correctness.
4. Implement a safe shared-credential publication/borrow/teardown contract across every `override_creds(ksu_cred)` caller, including synchronized lifetime, READY state, cleanup ordering, and failure unwinding. Raw `get_cred(ksu_cred)` without synchronization races teardown.
5. Independently address SU_SESSION FD ownership, post-exec authorization, and revocation. Do not mark release gates as passed prematurely.
6. Continue SUSFS conflict resolution and NoMount only after upstream dependencies and source-only gates are met.

## Existing validated boundaries
- KSUN-only integration workflow adjustment: `dd190317d0e7334885350da8cb11e755585b1909` (previous CI success).
- BakaSU combined workflow changed to manual-only: `c886dda8f4b2522fea42e1bc35d35d42cc7e1418`.
- Host-side candidate guard and tests are present; negative guard results are not proof of safe credential publication.
- SUSFS source conflicts and core placement remain unresolved; no proven full compile/link/runtime/ABI/KMI compatibility.
- NoMount integration remains pending.

## Recovery instruction
Resume from the branch HEAD and this checkpoint; preserve history. If a change is unsafe or unverifiable, leave it unmerged and record the blocker. Never infer that a CI failure is a device boot failure. The device kernel must not be modified as part of this checkpoint.
