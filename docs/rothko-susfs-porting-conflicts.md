# Rothko SUSFS upstream porting conflicts — read-only audit

## Evidence

- GitHub Actions provenance run: https://github.com/cogan17/Xiomi-14t-pro/actions/runs/38317695446
- Source: pinned Simonpunk SUSFS commit `5192aa2d33b381b58c1051532f9e1dfa5de6e8d3`.
- Result: official upstream GitLab source was fetched; compatibility audit exited with code 14 during patch applicability checks.
- KSUN independent candidate audit at the same revision passed; this is **not** a SUSFS compatibility or release approval.

## Confirmed rejected upstream hunks

- `fs/proc/base.c`: include-block context differs near line 100.
- `fs/proc/task_mmu.c`: `mem_size_stats` / VMA accounting context differs near line 883; other hunks had offsets.
- `mm/memory.c`: include-block context differs near line 79.

Earlier audit observations also identified `fs/exec.c` and `fs/namei.c` as conflict-sensitive. Inspect the full run log before declaring the conflict inventory complete.

## Porting order (no blind application)

1. Enumerate all rejected hunks from the exact pinned upstream patch and pinned Rothko BSP.
2. Separate include-only context drift from semantic changes to exec/namei, proc/VMA and memory.
3. Implement minimal BSP-specific port candidates in an isolated workspace; preserve upstream semantics and audit each hunk.
4. Require `git apply --check`, compile checks, negative/security contract tests, and runtime review before integration is considered.

**Release gate:** BLOCKED. No kernel source modification, merge, release or flashing authorized by this document.
