# Rothko / KernelSU Next + Simonpunk SUSFS — compatibility gate (experimental)

Status: **AUDIT ONLY — NO FLASH / NO MERGE / NO KERNEL IMAGE**.

## Scope
- Base: `dev/rothko` (Xiaomi Rothko BSP, not the BakaSU PR branch).
- KernelSU Next upstream: https://github.com/KernelSU-Next/KernelSU-Next
- Simonpunk SUSFS upstream: https://gitlab.com/simonpunk/susfs4ksu
- BakaSU PR #8 is preserved separately; do not transplant its BakaSU integration into KSUN.
- NoMount intentionally excluded from the first integration phase.

## Mandatory pre-build audit
1. Resolve and record immutable full commit SHAs for KSUN and SUSFS (including exact SUSFS Android 14 / 6.1 patch branch); **do not use floating dev/latest**.
2. Read KSUN's kernel integration instructions, SUSFS hook interface, Kconfig and Makefile requirements at those SHAs. Compare the exact SUSFS API and kernel hooks against KSUN; a manager APK swap alone is insufficient.
3. Audit Xiaomi BSP `6.1.57` context for all SUSFS patch hunks. Require strict `git apply --check --whitespace=error`, no fuzz/reject or invented compatibility macros.
4. Check all SUSFS feature checks and version guards; **never disable or spoof compatibility checks**. If an upstream mismatch exists, stop with diagnostic evidence.
5. Confirm KSUN can compile in-tree with `CONFIG_MODVERSIONS=y`, check symbol/CRC and vendor-module ABI/KMI compatibility; build success alone is not device compatibility.
6. Only after the above: isolated CI compile with no flashable ZIP or release artifact, no NoMount, and no automatic merge.
7. Independently audit boot/init_boot/vendor_boot, vendor modules, DTBO, device recovery/rollback before considering any device test.

## Reference only — not proof for Rothko
- WildKernels GKI releases list KSUN and SUSFS combinations for android14-6.1. These are generic GKI references, **not Xiaomi Rothko BSP validation**: https://github.com/WildKernels/GKI_KernelSU_SUSFS/releases
- Previous BakaSU CI #22 stopped in `kernel/tools/susfs_compat.mk` with `Please wait susfs update`. This guard is BakaSU-specific and does not prove KSUN compatibility.

## Gate status
- [x] Separate experimental branch from `dev/rothko`
- [x] Record integration policy and upstream references
- [ ] Pin KSUN and SUSFS full commit SHAs
- [ ] Complete hook/API and patch-context audit
- [ ] Complete ABI/KMI/vendor module checks
- [ ] Controlled CI compilation
- [ ] Device validation (not authorized)

**Fail closed:** no version spoofing, guard bypass, kernel image release, flash instruction, or merge based only on a green compile.

## Investigation findings (2026-10-12; source comparison pending)
- KernelSU Next official website advertises GKI 5.10–6.6 and SuSFS controls, but does **not** establish a matching SUSFS kernel-hook implementation for Xiaomi Rothko: https://kernelsu-next.github.io/webpage/
- WildKernels uses `pershoot/KernelSU-Next@dev-susfs` **for kernel integration**, while the KSUN manager is built from the official KSUN repository: https://github.com/WildKernels/GKI_KernelSU_SUSFS/blob/main/.github/workflows/main.yml
- WildKernels lists SUSFS android14-6.1 pin `24743360ea08d98f6ad72b856851abed8de5854f` and KSUN integration fork pin `3438d6aa431f96a23f9e625bec3d53ce1fb14161` in release records. These are **candidate reference pins only**; do not mark approved without confirming source history, exact branch, matching interface and licensing.
- WildKernels Samsung release notes explicitly warn that the pershoot integration is not production-ready, even if it works on other devices: https://github.com/WildKernels/Samsung_KernelSU_SUSFS/releases
- Historical upstream KSUN SUSFS compilation regression: https://github.com/KernelSU-Next/KernelSU-Next/issues/426
- GKI kernel family must follow stock KMI/firmware rather than Android userspace alone: https://github.com/WildKernels/GKI_KernelSU_SUSFS/blob/main/docs/build-from-fork.md

## Outstanding blockers
1. Inspect exact KSUN fork source and its SUSFS compatibility checks against the selected Simonpunk SHA; upstream git remote could not be directly queried in this investigation environment.
2. Verify whether the candidate SUSFS commit is a suitable ancestor/descendant of our BakaSU SUSFS pin; never infer compatibility from SHA recency.
3. Compare Xiaomi Rothko baseline against SUSFS patch hunks, with special focus on proc/maps VMA semantics and KMI generation.
4. Inspect vendor module symbol CRCs and DT/DTBO/boot chain independently.
5. Do not run a 27-minute build until compatibility preflight is genuinely supported by evidence; the current preflight requires human audit flags and is **not** proof by itself.

**Decision:** KSUN experiment remains audit-only. No source integration, compile, merge or flashing authorized by these findings.

## Second investigation — cross-check (2026-10-12)
- Official KSUN project states 6.1 GKI support but distinguishes GKI and Non-GKI paths; manager SUSFS controls do not imply kernel hook ABI compatibility: https://kernelsu-next.github.io/webpage/
- A KSUN maintainer's April 2026 comment reports legacy SUSFS / built-in SUSFS is **not specifically supported** on that path and suggests vanilla driver isolation during diagnosis; a different manager mode may behave differently: https://github.com/KernelSU-Next/KernelSU-Next/issues/1230
- KSUN `legacy_susfs` was reported outdated against main development in April 2026: https://github.com/KernelSU-Next/KernelSU-Next/issues/1215
- A separate historical KSUN/SUSFS regression produced `ksu_devpts_hook` undeclared identifier compiler errors; this is not evidence of the same error on Rothko: https://github.com/KernelSU-Next/KernelSU-Next/issues/426
- WildKernels reference release identifies KSUN fork SHA `3438d6aa431f96a23f9e625bec3d53ce1fb14161`, but its variant table may show SUSFS SHA as n/a; **do not claim** SUSFS SHA `24743360...` was verified for the same release/variant: https://github.com/WildKernels/GKI_KernelSU_SUSFS/releases
- The direct raw-source fetch and git remote inspection were unavailable in this environment, so the precise KSUN fork hook implementation, SUSFS patch content at the candidate SHA, and source-level API comparison **remain unverified**.
- The current preflight script only checks user-supplied approval environment variables; it is an administrative fail-closed gate, **not** a source-aware automated compatibility validator. Approval variables must never be set solely to force a green result.

### Additional decision
Continue **source-level audit only**. Do not pin a guessed SUSFS SHA, assert compatibility, compile, or merge. Next concrete dependency: obtain immutable upstream file contents and compare hooks plus kernel BSP context, then build real programmatic checks.

## Third investigation — developer statement and source access (2026-10-12)
- **Direct developer statement:** pershoot explicitly describes `pershoot/KernelSU-Next@dev-susfs` and `pershoot/susfs4ksu@gki-android14-6.1-dev` as personal development repos, intended to be in flux (May 31, 2026): https://github.com/KernelSU-Next/KernelSU-Next/issues/1293
- WildKernels main workflow uses `pershoot/KernelSU-Next@dev-susfs` for KSUN kernel-side integration when SUSFS is enabled, but official KSUN manager source; its Android14-6.1 SUSFS pin table includes `24743360ea08d98f6ad72b856851abed8de5854f`: https://github.com/WildKernels/GKI_KernelSU_SUSFS/blob/main/.github/workflows/main.yml
- KSUN official installation docs warn dev branch has not been fully tested: https://kernelsu-next.github.io/webpage/pages/installation.html
- Verified live source access limitation: container `git ls-remote` failed due DNS for github.com; direct GitHub pinned `kernel/Kbuild` page could not be fetched. **Do not claim any source-level hook comparison has been completed.**
- Explicitly distinguish **permission to run a non-flashable CI compile** from **permission to flash/merge**. Neither is approved yet: missing source-level interface comparison and vendor ABI/KMI evidence.
- **Next action required:** obtain readable immutable KSUN kernel source and Simonpunk patch source, inspect hook symbols/headers and `git apply --check` against Rothko; then prepare non-flashable isolated CI only after a clean preflight.

## Fourth investigation — verified pinned KSUN source (2026-10-12)
GitHub connector **successfully fetched source contents** at `pershoot/KernelSU-Next@3438d6aa431f96a23f9e625bec3d53ce1fb14161`:
- `kernel/Kbuild`: when `CONFIG_KSU_SUSFS=y`, excludes regular syscall hook objects; SUSFS section reads `SUSFS_VERSION` from `include/linux/susfs.h` when `fs/susfs.c` exists. This is a real conditional integration path, **not** evidence all hook interfaces match.
- `kernel/Kconfig`: `KSU_SUSFS` and feature switches `SUS_PATH`, `SUS_MOUNT`, `SUS_KSTAT`, `SPOOF_UNAME`, `OPEN_REDIRECT`, `SUS_MAP` are present.
- `kernel/Makefile`: standalone module build support exists; not equivalent to the in-tree Xiaomi BSP path.
- `kernel/tools/susfs_compat.mk`: 404 at this SHA/path, unlike BakaSU; **absence of this one file is not proof of compatibility**.
- WildKernels `.github/workflows/main.yml` was fetched directly, but its size and complexity require exact pin extraction before applying any recipes.
- Remaining blocking work: obtain exact Simonpunk SUSFS source at a pinned SHA, compare all KSUN SUSFS hook signatures and proc/maps changes against Rothko BSP, then validate Kconfig integration and `git apply --check`. No source code was changed and no CI build started.

## Fifth investigation — pinned KSUN call-site audit (2026-10-12)
Source read directly from `pershoot/KernelSU-Next@3438d6aa431f96a23f9e625bec3d53ce1fb14161`:
- `kernel/core/init.c:94-98` calls `susfs_init()` whenever `CONFIG_KSU_SUSFS` is enabled. Confirm the matching declaration and implementation exist in the selected SUSFS source and are safe at this init phase.
- `kernel/supercall/dispatch.c:1044-1145` implements `ksu_handle_sys_reboot(int magic1, int magic2, unsigned int cmd, void __user **arg)` and dispatches SUSFS commands. It references `SUSFS_MAGIC`, `CMD_SUSFS_*`, `susfs_add_sus_path_loop`, `susfs_set_avc_log_spoofing`, `susfs_get_enabled_features`, `susfs_show_variant`, `susfs_show_version`, among others. **Each** must be checked against the pinned SUSFS headers/implementation before a build.
- `kernel/Kbuild:22` excludes regular syscall hook objects under `CONFIG_KSU_SUSFS=y`, so the expected inline hooks must actually be present in the patched BSP. Check syscall signatures, config gates, symbol resolution, and LSM integration.
- **New concern:** `ksu_handle_sys_reboot` and its toolkit fallback must be checked for exact calling conventions and semantics in the Xiaomi BSP; do not assume generic GKI hook offsets.
- These are real source observations, not a completed API or vendor audit. No compile authorization yet.

## Sixth investigation — upstream pin provenance (2026-10-12)
- Read WildKernels `.github/workflows/main.yml` directly. Around line 332, it resolves `pershoot/KernelSU-Next.git refs/heads/dev-susfs` to a commit SHA; around lines 1476–1486 it selects/clones the `dev-susfs` branch. A floating branch must **not** be adopted without pinning its SHA and matching SUSFS source.
- Attempted `pershoot/susfs4ksu@24743360ea08d98f6ad72b856851abed8de5854f` paths `kernel_patches/fs/susfs.c`, `kernel_patches/include/linux/susfs.h`, and `kernel_patches/50_add_susfs_in_gki-android14-6.1.patch`; all returned GitHub 404. This may mean incorrect repo/path/ref/access and **does not prove** the upstream source lacks the files.
- Attempted `pershoot/susfs4ksu@gki-android14-6.1-dev` README; 404. Thus the alleged SUSFS candidate SHA has **not been verified** at that repository.
- **Audit blocker:** obtain authoritative Simonpunk GitLab patch/header/source or a verifiable fork and record exact provenance. Until then, KSUN call sites cannot be compared to SUSFS declarations and implementation. No source integration or build.

## Seventh investigation — verified SUSFS GitLab source and patch compatibility warning (2026-10-12)
- **Correct upstream location found:** pershoot SUSFS is hosted on **GitLab**, not GitHub: https://gitlab.com/pershoot/susfs4ksu/-/tree/gki-android14-6.1-dev . Previous GitHub 404 results were a repository-host mismatch, **not evidence the project was absent**.
- Official Simonpunk Android14/6.1 source: https://gitlab.com/simonpunk/susfs4ksu/-/tree/gki-android14-6.1 . The official branch explicitly warns that patches are built primarily against original KernelSU release tags, and kernel differences require custom patch review.
- Official Simonpunk KernelSU patch: https://gitlab.com/simonpunk/susfs4ksu/-/blob/gki-android14-6.1/kernel_patches/KernelSU/10_enable_susfs_for_ksu.patch . The indexed diff visibly changes `kernel/Kbuild`, `kernel/Kconfig`, `kernel/core/init.c`, `kernel/supercall/dispatch.c`, etc. **Do not blindly apply this original-KernelSU patch on top of pershoot KSUN**, which already contains SUSFS conditional code; doing so risks duplicated definitions or conflicting hooks.
- The official indexed patch includes SUSFS command identifiers `CMD_SUSFS_ADD_SUS_PATH_LOOP`, `CMD_SUSFS_SHOW_ENABLED_FEATURES`, `CMD_SUSFS_SHOW_VARIANT`, `CMD_SUSFS_SHOW_VERSION` and calls `susfs_add_sus_path_loop`, `susfs_get_enabled_features`, `susfs_show_variant`, `susfs_show_version`. These match names observed in pinned KSUN `kernel/supercall/dispatch.c`; **name matching is partial evidence, not header/prototype/ABI compatibility**.
- GitLab branch listing for pershoot `gki-android14-6.1-dev` shows active divergence from Simonpunk and is described as experimental. Must pin and audit exact paired GitLab/GitHub commits.
- Direct GitLab raw-file retrieval in the available tools failed and local git could not resolve gitlab.com. Therefore no complete SUSFS header/function-signature audit or `git apply --check` has been performed. Build gate stays closed.
