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

## Source-only Kconfig dependency review — 2026-10-14

- **External reference, not pinned proof:** the public Simonpunk `gki-android14-6.1` companion patch currently displays `config KSU_SUSFS` as a `bool` depending on `KSU` and `THREAD_INFO_IN_TASK`, with `default y`. This is a *moving branch* observation; it must be rechecked against the immutable `5192aa2` tree before being treated as the pinned contract.
- **Integration implications:** `depends on KSU` alone does not establish that SUSFS can safely link when `KSU=m`. The existing Rothko `fs/Makefile` candidate uses `obj-$(CONFIG_KSU_SUSFS) += susfs.o`; its isolated y/n/unset success proves only object selection, not linkage. Built-in-only behavior, Kconfig symbol ownership and compatibility with KSUN must be checked together.
- **Next bounded source-only action:** extract the `config KSU_SUSFS` block and adjacent `depends on` / `select` statements from the *pinned* companion patch, compare to Rothko Kconfig and candidate Makefile, then classify `KSU=y/m/n` against `KSU_SUSFS=y/n`. Do not create another CI or modify the kernel merely for this documentation review.
- **No promotion:** no claim of Kconfig compatibility, compile, link, ABI, runtime safety or release readiness. PR #9 remains Draft / BUILD HOLD.

## Verified pinned Kconfig declaration — run 38447497791

- [Source-audit run 38447497791, job 115469582345](https://github.com/cogan17/Xiomi-14t-pro/actions/runs/38447497791) completed **success** and printed the `KSU_SUSFS` declaration from the immutable SUSFS tree (`5192aa2`, verified tree `b39cd4`). This supersedes the earlier moving-branch-only evidence for this specific declaration.
- Verified patch block: `config KSU_SUSFS` is `bool`, `depends on KSU`, `depends on THREAD_INFO_IN_TASK`, `default y`. Additional SUSFS feature symbols depend on `KSU_SUSFS` and default to `y` in the inspected block.
- **Not cleared:** the isolated source-layout job does not validate Rothko's effective `.config`, KSU tristate/built-in linkage, upstream patch application, compiler/linker behavior, or runtime/credential/FD contracts. Other jobs in the run were still active when inspected. Do not describe the entire workflow as green on the basis of this job.
- **Next checkpoint:** inspect the Rothko Kconfig ownership of `KSU` and effective kernel config against the verified pinned declaration, without re-fetching or rerunning this already-successful layout job. Draft PR #9 and BUILD HOLD remain.

## CI status clarification — push runs and intentional blocker (2026-10-14)

- Earlier `fetch_commit_workflow_runs` queries returned empty because that helper filters to pull-request-triggered runs. Direct GitHub Actions branch-run listing confirmed **push** runs for the same commits; absence in that helper is **not** absence of CI.
- [Run 38447497791](https://github.com/cogan17/Xiomi-14t-pro/actions/runs/38447497791), commit `62474a1`: pinned `susfs-core-layout` job **success**. Other jobs were not yet complete at the time of inspection; do not claim whole-run success.
- [Run 38446329304](https://github.com/cogan17/Xiomi-14t-pro/actions/runs/38446329304), commit `aca5010`: layout and include-drift jobs **success**; `provenance` **failure (exit 14)** due to existing real integration blockers, including failed official SUSFS patch applicability (`fs/proc/task_mmu.c`, `mm/memory.c` and other conflicts), credential/session-FD proof, KSUN companion applicability, and execve/ARM64 source contracts. Do **not** rerun this to seek cosmetic green status.
- Next source-only task: identify effective Rothko `CONFIG_KSU` ownership/values and `THREAD_INFO_IN_TASK` availability; compare with the now-verified pinned `KSU_SUSFS` declaration. Do not duplicate CI or alter kernel source without a new actionable compatibility finding. PR remains Draft / BUILD HOLD.

## Rothko baseline config inspection — 2026-10-14

- Inspected actual PR-branch `arch/arm64/configs/gki_defconfig`, `arch/Kconfig`, and root `Kconfig`. No `CONFIG_KSU`, `THREAD_INFO_IN_TASK`, or direct KernelSU Kconfig source references were found in those three files by exact-text inspection.
- **Scope limit:** absence in these three files is **not** proof that KSUN is disabled; source-patch and build-time config fragments may introduce symbols. `THREAD_INFO_IN_TASK` may also be defined by architecture Kconfig outside these inspected files.
- Do not force `CONFIG_KSU_SUSFS=y`, assume `KSU=y`, or change kernel configuration until the exact KSUN Kconfig integration and effective `.config` generation path are established. The pinned SUSFS Kconfig declaration has already been verified in run 38447497791 and must not be reaudited.
- **Next:** inspect existing root integration workflow/scripts and any defconfig fragments for where KSUN is injected, then classify the actual configuration source. No additional CI is justified by this text inspection alone. PR Draft / BUILD HOLD.

## Rothko Kconfig entrypoint inspection — 2026-10-14

- Inspected the PR-branch files `Kconfig`, `drivers/Kconfig`, `fs/Kconfig`, and `arch/arm64/configs/gki_defconfig`. None contains a literal `KSU` or `SUSFS` declaration/reference; `gki_defconfig` also has no literal `THREAD_INFO_IN_TASK` entry. These are **specific file observations**, not proof the effective kernel config lacks the symbols.
- `scripts/rothko_susfs_source_probe.sh` explicitly acquires pinned external KSUN and SUSFS sources for source-only auditing. The current repository's Kconfig entrypoints do not yet establish how external KSUN Kconfig is wired into the BSP or whether the target build config satisfies `THREAD_INFO_IN_TASK`.
- **Next non-duplicative gate:** inspect the pinned KSUN Kconfig and its intended source/include hook against the Rothko tree, and determine the effective config via the actual target build configuration before proposing a source integration. Do not add speculative `source` directives or force config values.
- No kernel changes, new CI, or merge authorized; Draft PR #9 / BUILD HOLD.
