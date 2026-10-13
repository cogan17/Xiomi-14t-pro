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

## Verified include dependency evidence (read-only audit, 2026-10-13)

CI run [38321629204](https://github.com/cogan17/Xiomi-14t-pro/actions/runs/38321629204) independently reports five inspected patch hunks each adding `#include <linux/susfs_def.h>`; the directive is absent from the pristine Rothko BSP files inspected. Each of these hunks also contains other nonblank additions (four with two, one with nine). They are **mixed hunks**, not safely skippable or automatically applicable include-only changes.

The official pinned 6.1 patch still fails `git apply --check`, including `fs/namei.c`, `fs/proc/base.c`, `fs/proc/task_mmu.c`, and `mm/memory.c`. In particular the `mm/memory.c` failure at upstream context near line 79 is not proof of a missing SUSFS header alone; it is a mismatch of surrounding BSP include context. A hunk's context lines appearing somewhere in the file does not establish a safe application location.

**Porting order:** first verify the SUSFS header and dependency provenance against the pinned upstream tree, then reconcile each conflicting hunk against exact Rothko BSP functions, then validate the KSUN companion patch and credential/FD, execve, and ARM64 flag contracts. Keep the candidate source-only and PR Draft. Do not bypass the release blockers, auto-fuzz patch offsets, build a flashable image, or merge on the strength of this classification report.

## Checkpoint ROTHKO-ACA5010 — Kconfig evidence boundary (2026-10-14)

- Existing `susfs-core-layout` job inventories upstream `susfs.c` (including patch-added paths), `susfs.h` / `susfs_def.h`, Kconfig paths touched by the official pinned kernel patch, and textual references to `CONFIG_KSU_SUSFS` / `susfs.o`.
- **Not proven:** Kconfig symbol declaration, `depends on` / `select` semantics, kernel built-in vs module behavior, transitive header requirements, compile/link success, or compatibility with the pinned KSUN companion and Rothko BSP. An inventory PASS must not clear these gates.
- Do not duplicate existing source audits or launch a fresh CI merely to restate these limitations. The next source-only decision should use actual job evidence and inspect exact Kconfig declaration/dependency blocks before proposing a BSP-specific candidate.
- **Efficiency rule:** reuse validated candidates; at most two attempts for the same approach, stop after the first success. PR remains Draft; BUILD HOLD and all runtime/security blockers remain unchanged.
