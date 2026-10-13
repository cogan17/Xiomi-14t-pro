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

## Verified KSUN integration entrypoint — 2026-10-14

- Inspected immutable `pershoot/KernelSU-Next@3438d6aa431f96a23f9e625bec3d53ce1fb14161`, `kernel/Kconfig` and `kernel/setup.sh` (not a moving branch). `config KSU` is `tristate`, `depends on KPROBES || SUSFS`; `config KSU_SUSFS` is `bool`, `depends on KSU`, `depends on THREAD_INFO_IN_TASK`.
- Pinned `kernel/setup.sh` injects `obj-$(CONFIG_KSU) += kernelsu/` into `drivers/Makefile` and `source "drivers/kernelsu/Kconfig"` into `drivers/Kconfig` (assuming the KSUN source has been placed at that directory).
- Inspected PR-branch `drivers/Makefile` and `drivers/Kconfig`: neither contains the KSUN integration directives. Thus the **in-tree entrypoint is not wired in the inspected branch**. This is not evidence that a separate downstream build process cannot inject KSUN; the actual build/integration path still needs identification.
- Next bounded task: trace any documented external source injection/build integration before creating a candidate hook. Do not blindly run setup.sh or insert duplicate hooks. No new CI or device build; PR #9 remains Draft / BUILD HOLD.

## Existing isolated root-driver installer and pin mismatch — 2026-10-14

- `scripts/rothko_install_root_driver.py` already provides an isolated-checkout Kconfig/Makefile integration path; it checks the Xiaomi 6.1.57 baseline and KMI generation 11, refuses an existing `drivers/kernelsu` entry, and does **not** invoke upstream `setup.sh` or integrate SUSFS. Do not add duplicate in-tree hooks.
- **Critical provenance distinction:** the installer's `KernelSU-Next` entry currently pins `KernelSU-Next/KernelSU-Next@02a9e1c5fb2c4fd8117429fe004136332788c1b6`, while this PR's SUSFS compatibility audit pins `pershoot/KernelSU-Next@3438d6aa431f96a23f9e625bec3d53ce1fb14161`. These are different repositories and commits. The installer therefore **cannot be treated as an approved installer for the audited KSUN pin**; its existing pin validation would reject that source.
- **Next decision gate:** identify which exact KSUN repository/commit is the intended integration target, then align the installer and provenance rules only after explicit source compatibility review. Do not silently change pins, execute installer, or run another build/CI to conceal this mismatch. PR #9 remains Draft / BUILD HOLD.

## Build-config and existing smoke gate — 2026-10-14

- Inspected `build.config.gki.aarch64`: it conditionally sources `GKI_BUILD_CONFIG_FRAGMENT`, but this is **not evidence** that any specific KSUN or SUSFS config fragment is active for the Rothko target.
- Inspected `scripts/rothko_bsp_compile_smoke.sh`: its existing smoke gate checks the generated `out/.config` for enabled `CONFIG_KSU`, `CONFIG_KSU_SUSFS` or `CONFIG_KERNELSU` variants. Reuse this guard; do not duplicate it with another CI job.
- The installer pin mismatch (`KernelSU-Next/KernelSU-Next@02a9e1c5` versus audit `pershoot/KernelSU-Next@3438d6aa`) remains unresolved. No automatic pin replacement, source injection or Kconfig edit is justified.
- Next checkpoint: establish which build config/fragment the Rothko target actually selects, and trace whether its generated `.config` is produced before the existing smoke guard. This remains a source-only inspection; no kernel compilation or workflow rerun.

## Effective config gate: generic smoke is deliberately root-free — 2026-10-14

- Verified exact `scripts/rothko_bsp_compile_smoke.sh` behavior: `config` invokes `make O=out ARCH=arm64 LLVM=1 LLVM_IAS=1 gki_defconfig`, then **rejects** enabled `CONFIG_KSU`, `CONFIG_KSU_SUSFS` and `CONFIG_KERNELSU` variants in `out/.config`. It explicitly labels the result generic GKI and **not verified for Rothko**.
- `build.config.gki` declares `DEFCONFIG=gki_defconfig`; `build.config.aarch64` declares `ARCH=arm64`; `build.config.gki.aarch64` may source `GKI_BUILD_CONFIG_FRAGMENT`, but the smoke script does not use that build-config mechanism. Therefore a passing smoke check must **not** be promoted to KSUN/SUSFS compatibility proof.
- Existing installer remains an isolated-checkout integration tool with a different KSUN repository/commit pin from PR #9's audit. Resolve that provenance decision before creating any root-enabled configuration candidate.
- **Next:** inspect existing Rothko-specific workflow/build entrypoints to determine whether a separate approved root-enabled config path exists; do not alter generic smoke, launch a compile, or add redundant CI. PR #9 stays Draft / BUILD HOLD.

## Existing root-enabled CI path — 2026-10-14

- Inspected `.github/workflows/rothko-root-integration.yml`: it already runs isolated source integration for separate root flavors, including KSUN `KernelSU-Next/KernelSU-Next@02a9e1c5`, and has a **BakaSU-only** experimental `compile-bakasu` job. That job uses `gki_defconfig`, enables `CONFIG_KSU` and `CONFIG_KSU_TRACEPOINT_HOOK`, **disables `CONFIG_KSU_SUSFS`**, runs `olddefconfig`, and labels the resulting Image **non-flashable**.
- This is an existing **root-enabled diagnostic path**, but **not** a KSUN+SUSFS build path and not a Rothko device-boot proof. The source audit PR pins a different KSUN (`pershoot@3438d6aa`); do not reuse the older KSUN installer matrix as evidence for that pin.
- No need for a new root-enabled workflow: the next meaningful step is to resolve the intended KSUN provenance and existing SUSFS/security blockers before changing any root-enabled CI. Keep generic smoke root-free and BakaSU experimental flow unchanged.
- Source-only documentation checkpoint; no CI dispatch, compile, integration, merge, or release. PR #9 Draft / BUILD HOLD.

## Origin of the two KSUN pins — 2026-10-14

- Branch-scoped GitHub file history identifies commit `5c438f9563c744963a98f5cdada09e1ce0c0ed17` (2026-10-12), `feat(rothko): integrate pinned KSU KSUN BakaSU with ARM64 compile verification`, as the introducing commit for `scripts/rothko_install_root_driver.py`.
- The same commit introduces an isolated three-flavor integration workflow with `KernelSU-Next/KernelSU-Next@02a9e1c5fb2c4fd8117429fe004136332788c1b6`. This pin belongs to the **experimental root-driver integration** path, not to the independent KSUN+SUSFS audit.
- The independent candidate workflow explicitly fetches `pershoot/KernelSU-Next@3438d6aa431f96a23f9e625bec3d53ce1fb14161`. Their different provenance is intentional at the workflow boundary; no evidence yet proves interchangeable code or an approved migration.
- **Disposition:** preserve both pins and existing guards. Do not rewrite the installer, add a second integration path, run CI, or assert compatibility. Next technical gate is a targeted source/API compatibility comparison only if it can resolve a concrete integration decision. PR #9 remains Draft / BUILD HOLD.

## Targeted immutable KSUN Kconfig comparison — 2026-10-14

Compared `kernel/Kconfig` directly at the **exact two pinned commits**, not their moving branches:

| Contract | Experimental installer `KernelSU-Next/KernelSU-Next@02a9e1c5` | SUSFS audit `pershoot/KernelSU-Next@3438d6aa` |
| --- | --- | --- |
| `config KSU` | `tristate`, `depends on KPROBES && EXT4_FS` | `tristate`, `depends on KPROBES || SUSFS` |
| `config KSU_SUSFS` in this file | **Absent** | `bool`, `depends on KSU`, `depends on THREAD_INFO_IN_TASK`, `default y` |

- The Kconfig contracts are **not equivalent**. The installer source cannot be treated as a drop-in replacement for the audited KSUN+SUSFS source. Absence of `KSU_SUSFS` is scoped to the inspected upstream `kernel/Kconfig` file, not an assertion about all downstream patches.
- Keep the installer matrix pinned to its original source; do not change the audited `pershoot` pin or automatically enable SUSFS. Next useful review is the relevant Kbuild/SUSFS API surface at these same immutable commits, without rebuilding or repeating the Kconfig comparison.
- PR #9 remains Draft / BUILD HOLD; no CI rerun, source integration, or device operation.

## Targeted immutable KSUN Kbuild comparison — 2026-10-14

- Compared exact pinned upstream `kernel/Kbuild`, `kernel/Makefile`, and `kernel/setup.sh` for installer `KernelSU-Next/KernelSU-Next@02a9e1c5` versus audit `pershoot/KernelSU-Next@3438d6aa`.
- **Material Kbuild difference:** the audit pin conditionally excludes or selects hook objects under `ifneq ($(strip $(CONFIG_KSU_SUSFS)),y)`; the installer pin's inspected Kbuild does not contain that SUSFS selection branch. Therefore compiled hook selection is **not equivalent** for SUSFS-enabled configurations, in addition to the previously proven Kconfig differences.
- Both pinned setup scripts expose the existing `drivers/kernelsu` Makefile/Kconfig wiring pattern. Rothko's isolated installer already owns this wiring; **do not duplicate it** or run upstream setup.sh in-tree.
- Scope: static Kbuild comparison only; no claim of full API compatibility, successful link, runtime safety, or ready-to-flash kernel. Preserve both pins, all existing candidates and gates. Next gate is the **specific SUSFS companion/API contract**, not a repeated broad Kconfig/Kbuild audit.

## Targeted pinned KSUN sucompat FD / post-exec check — 2026-10-14

- Inspected immutable `pershoot/KernelSU-Next@3438d6aa431f96a23f9e625bec3d53ce1fb14161` `kernel/feature/sucompat.c` and `kernel/feature/sucompat.h` (no build).
- Neither inspected file contains the identifiers `ksu_handle_post_execveat_sucompat` or `ksu_install_fd`. This is a **file-scoped negative observation**, not proof those identifiers are absent from every upstream file or that the companion patch cannot add them.
- The existing `sucompat.c` exec interception uses `get_unused_fd_flags(O_CLOEXEC)`, `filp_open(KSUD_PATH, O_PATH, 0)`, `fd_install(tmp_fd, ksud_file)`, `escape_with_root_profile()`, then invokes the execveat syscall path. The temporary executable FD must **not** be equated with a privileged post-exec `SU_SESSION` FD.
- Official pinned companion patch is already inspected by `.github/workflows/rothko-susfs-source-audit.yml`; no duplicate workflow or upstream fetch is needed. **HOLD** post-exec authorization, FD ownership/revocation, credential lifecycle and full KSUN/SUSFS integration until their combined contract is proven.
