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
