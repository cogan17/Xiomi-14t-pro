# Rothko BSP — resume checkpoint (2026-10-14)

**State:** PR #9 Draft; base `dev/rothko`, head `feat/rothko-ksun-susfs-compat-audit`. **BUILD HOLD**: no kernel build, merge, release, boot image or flashing. GitHub last reported `mergeable_state: dirty`; do not resolve by discarding existing work.

## Verified successes — preserve

- KSUN immutable upstream: `pershoot/KernelSU-Next@3438d6aa431f96a23f9e625bec3d53ce1fb14161`.
- SELinux precommit candidate `patches/rothko-ksun-selinux-precommit-gate-candidate.patch` was fixed at `b498c2abb277976791e67ed53c851b1b8c2cfdb0`. Independent KSUN candidate audit [run 38452401763](https://github.com/cogan17/Xiomi-14t-pro/actions/runs/38452401763) **SUCCESS**, including pinned-source `git apply --check --verbose` and 41 successful job steps. Source applicability only, **not** security, compile or runtime approval.
- Isolated SUSFS proc/memory workflow [run 38438911909](https://github.com/cogan17/Xiomi-14t-pro/actions/runs/38438911909) and [run 38438905268](https://github.com/cogan17/Xiomi-14t-pro/actions/runs/38438905268) **SUCCESS** at `6d6e9afd8dfa95a7b82ad2882dd27c4f3304346f`. Includes isolated BSP application checks for memory, smaps, rollup, pagemap, proc map_files/readlink, namei and consolidated task_mmu. Do **not** rerun these merely for another green status.
- Existing candidate patches and prior work must be preserved; no duplicate patches or workflows.

## Outstanding blockers

1. Official pinned SUSFS 6.1 integration still fails source applicability in the separate provenance audit (exit 14). Conflicts involve `fs/exec.c`, `fs/namei.c`, `fs/proc/base.c`, `fs/proc/task_mmu.c`, `mm/memory.c`; isolated candidate PASS does not clear the full integration gate.
2. KSUN companion integration, credential/SELinux fail-closed semantics, post-exec session FD ownership/lifetime, execve and ARM64 TIF contracts, effective Kconfig, ABI/KMI, compile and runtime are not approved.
3. PR #9 remains in GitHub merge conflict (`dirty`) against `dev/rothko` as last checked.

## Next action on resume

**Do not repeat successful audits.** Investigate PR #9's actual merge-conflicting files and determine a minimal non-destructive reconciliation plan. Separately use existing SUSFS isolated evidence to target only unresolved integration contracts; do not interpret source-only PASS as deployability. No build, merge or flashing until all gates are cleared.

**User paused work to sleep; this checkpoint is the handoff.**
