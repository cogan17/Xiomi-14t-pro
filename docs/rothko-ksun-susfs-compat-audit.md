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
