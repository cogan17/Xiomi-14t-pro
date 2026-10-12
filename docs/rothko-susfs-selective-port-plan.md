# Rothko SUSFS selective port — execution plan

Status: **SOURCE-ONLY / DRAFT / RELEASE BLOCKED**. This plan supersedes repetitive CI-only classification iterations; it does not replace the pinned upstream or approve flashing.

## Source of truth
- Target: Xiaomi 14T Pro (rothko), BSP Linux 6.1.57, branch `dev/rothko`.
- KernelSU-Next: `pershoot/KernelSU-Next@3438d6aa431f96a23f9e625bec3d53ce1fb14161`.
- SUSFS: `simonpunk/susfs4ksu@5192aa2d33b381b58c1051532f9e1dfa5de6e8d3`; tree `b39cd4117178ce73d2973f7bcdae5c74defc8f68`.
- Official source patch: `kernel_patches/50_add_susfs_in_gki-android14-6.1.patch`.
- Companion patch: `kernel_patches/KernelSU/10_enable_susfs_for_ksu.patch`.

## Ordered implementation slices
1. **Provenance and exact BSP base:** independently verify pinned commits/tree and actual Rothko BSP source revision; never silently follow upstream HEAD.
2. **Header/config prerequisites:** locate `susfs_def.h`, related declarations and Kconfig/Makefile dependencies; produce a complete file manifest, not a header-only workaround.
3. **VFS/namei:** reconcile `fs/namei.c` with Rothko lookup/open/tmpfile/readlink control flow; keep per-hunk semantic notes and explicit no-op/rollback behavior.
4. **proc and memory:** reconcile `fs/proc/base.c`, `fs/proc/task_mmu.c`, `mm/memory.c`; review VMA accounting and locking, not only line offsets.
5. **exec and KSUN:** reconcile `fs/exec.c` and companion KSUN patch; require authorization **before** `commit_creds`, validated session FD lifecycle, SELinux and seccomp semantics, and ARM64 TIF collision audit.
6. **Isolated validation:** exact-tree patch checks, compilation/static analysis and negative security tests. Source-level success alone never authorizes runtime use.

## Acceptance evidence per slice
Record upstream file and hunk, Rothko equivalent function/context, rationale for each changed line, source patch checksum, application test, semantic regression test, and remaining risks. Keep each slice reviewable and independently revertible.

## Explicit stop conditions
Stop rather than bypass: missing source provenance, ambiguous VFS/exec semantics, credential changes without prior authorization, unverified FD/session lifetime, unreviewed TIF flag collision, or compilation failure.

## Operational policy
Keep PR #9 Draft. Do not merge, create a flashable artifact, release, or flash. Preserve successful KSUN work and the original upstream patch unchanged. GitLab connectivity alone removes only the transport hold; compatibility and security gates remain active.


## BSP identity and provenance checkpoint (before any source edit)

The public MiCode kernel index identifies `bsp-rothko-u-oss` with Redmi K70 Ultra, while `bsp-degas-u-oss` is listed for Xiaomi 14T. Device marketing names and sibling devices are **not** proof of binary-compatible kernel source. Before editing a SUSFS hunk, record the exact checked-out BSP commit, `Makefile` kernel version, configuration/defconfig, device tree targets, and evidence that this is the source used for the intended Xiaomi 14T Pro build.

**Gate BSP-01:** reject assumptions based only on `rothko` codename, Android 14, or Linux 6.1; validate the repository's pinned base and build metadata against the target. Do not substitute `degas` source or an unrelated GKI tree.

**Gate PATCH-01:** for each upstream rejected hunk, capture both its original upstream function and its Rothko function counterpart before authoring a change. A passing textual apply check is not sufficient for VFS, VMA, exec, or privilege behavior.

**Evidence state:** source identity and complete upstream header manifest still need exact-tree verification; neither is claimed as passed here.
