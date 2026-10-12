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
