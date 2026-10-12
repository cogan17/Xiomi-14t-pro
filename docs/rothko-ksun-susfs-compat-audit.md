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

## Eighth investigation — concrete KSUN/Simonpunk patch overlap (2026-10-12)
Source: GitLab-indexed official Simonpunk `kernel_patches/KernelSU/10_enable_susfs_for_ksu.patch` on `gki-android14-6.1` (search snapshot, not pinned raw bytes); compared with directly fetched `pershoot/KernelSU-Next@3438d6aa431f96a23f9e625bec3d53ce1fb14161` files.
**Verified overlap**:
1. Simonpunk patch adds `CONFIG_KSU_SUSFS` in `kernel/Kconfig`; pershoot KSUN already defines it.
2. Simonpunk patch changes `kernel/Kbuild` to remove syscall hook objects and add SUSFS version detection; pershoot KSUN already has conditional exclusion and version detection.
3. Simonpunk patch inserts `susfs_init()` in `kernel/core/init.c`; pershoot KSUN already calls it when `CONFIG_KSU_SUSFS`.
4. Simonpunk patch adds `ksu_handle_sys_reboot` and SUSFS command dispatch in `kernel/supercall/dispatch.c`; pershoot KSUN already implements the function.
**Decision**: the generic Simonpunk **KernelSU integration patch is not an appropriate direct input to this KSUN fork**. Do not apply it wholesale. Instead, treat pershoot KSUN as kernel-side integration and select only matching **Linux kernel-side SUSFS patches** after exact-source verification. These overlapping additions are concrete duplicate/conflict risks, not a substitute for a dry-run.
**Unresolved**: raw Simonpunk `susfs.h`, `susfs_def.h`, `fs/susfs.c`, exact kernel patch and commit SHA; GitLab raw/API and git clone unavailable from this environment, and GitLab web pages return loading. Full signature/ABI comparison and `git apply --check --whitespace=error` remain unperformed. No CI compile.

## Ninth investigation — direct three-file candidate examination (2026-10-12)
- Attempted Simonpunk GitLab raw `kernel_patches/include/linux/susfs.h`, `susfs_def.h`, `kernel_patches/fs/susfs.c` via web: access disabled. Local git clone failed DNS. **Official GitLab bytes remain unverified.**
- GitHub code search located a third-party mirror `ShirkNeko/susfs4ksu@3bff1eb7b9d6e9465d6fe40df1bbb7dea43737a9`. Fetched its `kernel_patches/include/linux/susfs.h` (8,324 bytes; blob c6cb4a032cac60e3f0df59254b6bc24f8c34874c) and `kernel_patches/fs/susfs.c` (51,401 bytes; blob 586909bdc63fc3a59713d3edd5cd4caed3c1000b). The header declares `void __init susfs_init(void)` and implementation defines it, matching the KSUN init call.
- **Confirmed interface mismatch with this mirror**: its header defines older `CMD_SUSFS_ADD_SUS_MOUNT`, `CMD_SUSFS_ADD_SUS_MAPS`, etc., but lacks `CMD_SUSFS_ADD_SUS_PATH_LOOP`, `CMD_SUSFS_SHOW_VERSION`, `CMD_SUSFS_SHOW_VARIANT`, and `CMD_SUSFS_SHOW_ENABLED_FEATURES` referenced by pinned pershoot KSUN `kernel/supercall/dispatch.c`. Direct use is rejected; this is **not** a conclusion about official Simonpunk or pershoot GitLab versions.
- `kernel_patches/include/linux/susfs_def.h` was 404 on that mirror SHA; whether it exists elsewhere or in the official source is unknown.
- The Rothko base branch `dev/rothko` does not have these three files at root paths `include/linux/susfs.h`, `include/linux/susfs_def.h`, `fs/susfs.c` (404), as expected for unintegrated source; absence alone does not establish patch applicability.
- **Gate:** require complete pinned official/fork header and implementation, full API symbol and structure comparison, plus kernel patch dry run before CI compile. No file was copied from the rejected mirror into Rothko.

## Tenth investigation — all three SUSFS files obtained from an independent snapshot (2026-10-12)
- GitLab raw links for Simonpunk and pershoot remain inaccessible through web fetch (DisabledError); this **does not** establish upstream compatibility.
- GitHub code search identified an independent integrated SUSFS snapshot: `crdroidandroid/android_kernel_xiaomi_sm8150@f9ef69053739a482d867f028db97887fc9aa4ac9`. Directly fetched:
  - `include/linux/susfs.h` 9,099 bytes, blob `f9ef61d99dad05007972b7dea3ca1cd93f0a02de`, `SUSFS_VERSION "v2.3.0"`;
  - `include/linux/susfs_def.h` 4,747 bytes, blob `73e6e7cbe5b8e4c633aa3e2ed9c5b60547094e2b`;
  - `fs/susfs.c` 60,575 bytes, blob `e88dde044c40a91695a0700874bcde71366a8fbc`.
- In this snapshot, `susfs.h` declares and `fs/susfs.c` defines: `susfs_add_sus_path_loop(void __user **)`, `susfs_set_avc_log_spoofing(void __user **)`, `susfs_get_enabled_features(void __user **)`, `susfs_show_version(void __user **)`, and `susfs_init(void)`. The first four correspond to calls in pinned pershoot KSUN dispatcher; these **specific prototypes and implementations agree internally** in this snapshot.
- This is **a reference snapshot from another device**, not a verified matching Simonpunk/pershoot commit pair, and must **never** be copied into Rothko without provenance, kernel-version and patch analysis. Its v2.3.0 label alone is insufficient to infer compatibility.
- Remaining audit: compare complete `susfs_def.h` constants and struct layouts against pinned KSUN/userspace; enumerate all called symbols; acquire matching GitLab patch and SHA; dry-run against Xiaomi BSP and validate ABI/KMI. Gate stays closed.

## Eleventh investigation — complete SUSFS dispatcher symbol inventory (2026-10-12)
Direct byte-level comparison of pinned `pershoot/KernelSU-Next@3438d6aa431f96a23f9e625bec3d53ce1fb14161:kernel/supercall/dispatch.c` against the **reference-only** `crdroidandroid/android_kernel_xiaomi_sm8150@f9ef69053739a482d867f028db97887fc9aa4ac9` `include/linux/susfs.h`, `include/linux/susfs_def.h`, `fs/susfs.c`:
- 16 distinct `susfs_*` function calls appear in the KSUN dispatcher. **15** have both a named declaration in `susfs.h` and implementation in `fs/susfs.c`; the exception is `susfs_is_current_proc_no_su()`, referenced at dispatcher line 478, absent in both SUSFS reference files. This could be a KSUN-defined helper elsewhere; **do not declare a link error until its owner is identified**.
- Matched functions: `susfs_add_open_redirect`, `susfs_add_sus_kstat`, `susfs_add_sus_map`, `susfs_add_sus_path`, `susfs_add_sus_path_loop`, `susfs_enable_log`, `susfs_get_enabled_features`, `susfs_set_avc_log_spoofing`, `susfs_set_cmdline_or_bootconfig`, `susfs_set_hide_sus_mnts_for_non_su_procs`, `susfs_set_uname`, `susfs_show_variant`, `susfs_show_version`, `susfs_start_sdcard_monitor_fn`, `susfs_update_sus_kstat`.
- Reference `susfs_def.h` contains `SUSFS_MAGIC 0xFAFAFAFA`, `CMD_SUSFS_ADD_SUS_PATH_LOOP 0x55553`, `CMD_SUSFS_SHOW_VERSION 0x555e1`, `CMD_SUSFS_SHOW_ENABLED_FEATURES 0x555e2`, `CMD_SUSFS_SHOW_VARIANT 0x555e3`, `CMD_SUSFS_ADD_SUS_MAP 0x60020`; these are the names used in the KSUN dispatcher. No proof yet that manager/ksud uses matching numeric constants for every command.
- Reference `fs/susfs.c` includes private `fs/mount.h` and `fs/fuse/fuse_i.h`; both are **BSP-sensitive dependencies** requiring inspection of Rothko file paths and type definitions.
- This is a **name-presence audit**, not exhaustive prototype/type-layout matching; **the reference snapshot is a different device/kernel and is NOT approved for integration**. No `git apply --check` or build.

## Twelfth investigation — C signatures and userspace ABI (2026-10-12)
Directly compared pinned KSUN dispatcher against the immutable **reference-only** SUSFS v2.3.0 snapshot:
- All **15** SUSFS functions found in both `susfs.h` and `fs/susfs.c` have **matching C function signatures** between declaration and definition. Fourteen use `void (void __user **user_info)`; `susfs_start_sdcard_monitor_fn` uses `void (void)`. `susfs_is_current_proc_no_su()` is the **16th** dispatcher call, absent from those two reference files and requires symbol ownership investigation elsewhere in KSUN or kernel.
- Pinned KSUN `userspace/ksud/src/susfsd.rs` contains `SUSFS_MAGIC=0xFAFAFAFA` and `CMD_SUSFS_SHOW_VERSION=0x555e1`, matching reference `susfs_def.h`; the userspace reboot syscall passes magic1, SUSFS_MAGIC, command, and pointer. This is **partial wire protocol agreement**, not full binary structure-layout proof.
- `ksu_handle_sys_reboot` checks `magic1 == KSU_INSTALL_MAGIC1` and for SUSFS commands additionally `magic2 == SUSFS_MAGIC && current_uid().val == 0`. This is a code-level authorization gate; real-world hook dispatch and SELinux effects remain untested.
- Reference header defines multiple `struct st_susfs_*` including `st_susfs_version`, `st_susfs_variant`, `st_susfs_enabled_features`, `st_susfs_uname`, and `st_susfs_avc_log_spoofing`. **Field offsets, packing, sizeof, endianness, userspace Rust ABI, and runtime behavior have NOT yet been measured or tested.**
- Cannot assert complete structural or runtime compatibility without the exact paired upstream SUSFS sources and an instrumented build/runtime test; this is a bounded static signature/constant audit only. No CI build or flash approval.

## Thirteenth investigation — source-level runtime gating concern (2026-10-12)
- `pershoot/KernelSU-Next@3438d6aa...:kernel/supercall/dispatch.c:475-483`: `KSU_MARK_GET` under `CONFIG_KSU_SUSFS` invokes `susfs_is_current_proc_no_su()` and maps its boolean to a mark-status result. **This changes the mark query semantics** relative to the non-SUSFS branch, which calls `ksu_get_task_mark(cmd.pid)`. Confirm intended pid/current-task behavior and flag initialization before runtime testing.
- GitHub code search located `static inline bool susfs_is_current_proc_no_su(void)` in `include/linux/susfs_def.h` in other kernel trees (e.g. `crdroidandroid/android_kernel_oneplus_sm8350@5bc46e7124dce0c9a1880ac684d4a2d06fb87880`), using `test_thread_flag(TIF_PROC_NO_SU)`. **Our v2.3.0 reference `susfs_def.h` does not contain this helper**, so the 16th symbol gap is real for that snapshot and cannot be dismissed as a function in `fs/susfs.c`.
- Need check `TIF_PROC_NO_SU` availability/bit allocation in Rothko arm64 `thread_info.h`, exact matched SUSFS header, and whether `KSU_MARK_GET` semantics are intentional. Do not add a stub, define an arbitrary thread flag, or bypass this gate.
- No runtime test on the user's device was performed. User authorization is for **controlled diagnostics after compatibility proof**, not flashing.
