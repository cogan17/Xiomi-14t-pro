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
