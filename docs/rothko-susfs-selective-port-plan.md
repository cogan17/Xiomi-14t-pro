# Rothko SUSFS selective port — execution plan

Status: **SOURCE-ONLY / DRAFT / RELEASE BLOCKED**. This plan supersedes repetitive CI-only classification iterations; it does not replace the pinned upstream or approve flashing.

## Source of truth
- Target: Xiaomi 14T Pro (rothko), BSP Linux 6.1.57, branch `dev/rothko`.
- KernelSU-Next: `pershoot/KernelSU-Next@3438d6aa431f96a23f9e625bec3d53ce1fb14161`.
- SUSFS: `simonpunk/susfs4ksu@5192aa2d33b381b58c1051532f9e1dfa5de6e8d3`; tree `b39cd4117178ce73d2973f7bcdae5c74defc8f68`.
- Official source patch: `kernel_patches/50_add_susfs_in_gki-android14-6.1.patch`.
- Companion patch: `kernel_patches/KernelSU/10_enable_susfs_for_ksu.patch`.

## Resolved exact-source exec mapping (2026-10-14) — scope locked

- **GitLab source remains authoritative:** `simonpunk/susfs4ksu@5192aa2d33b381b58c1051532f9e1dfa5de6e8d3` (tree `b39cd4117178ce73d2973f7bcdae5c74defc8f68`). An independently accessible [ShirkNeko Git mirror at that identical commit](https://github.com/ShirkNeko/susfs4ksu/tree/5192aa2d33b381b58c1051532f9e1dfa5de6e8d3) reports **both Git commit and tree SHA identical**; this is content identity, not permission to use its moving branch. Official patch file `kernel_patches/50_add_susfs_in_gki-android14-6.1.patch` blob `b7b223bbe7aa33602b3a3b341568dd9d0606b11a`; official companion `kernel_patches/KernelSU/10_enable_susfs_for_ksu.patch` blob `7ebb9d5ef3a15682470236ae14ec53d9c17b5767`; header `kernel_patches/include/linux/susfs_def.h` blob `a021078ceaaaf6dc098dfdbed592c268c81f85b3`. These are pinned Git blobs, not local ports. No third-party branch drift is accepted.
- **Hunk 1 — `@@ -64,6 +64,9 @@`:** adds `#ifdef CONFIG_KSU_SUSFS` + `#include <linux/susfs_def.h>`. Our existing `rothko-susfs-exec-include-candidate.patch` covers this *limited include intent* using Rothko's actual include context. Upstream GKI lines after include differ from Xiaomi BSP; never claim the original hunk itself applied.
- **Hunk 2 — `@@ -1903,6 +1906,17 @@` after `bprm_execve`:** declares `ksu_su_compat_enabled`, `susfs_is_sdcard_android_data_not_decrypted` static keys and three entry points: `ksu_handle_execveat`, `ksu_handle_execveat_sucompat` and **`ksu_handle_post_execveat_sucompat`**. Our typed adapter only uses the first prehook. **The posthook declaration/implementation is absent in pinned pershoot `3438d6aa`**; do not borrow the official-KernelSU implementation without a new session/FD security contract.
- **Hunk 3 — `@@ -1910,10 +1924,28 @@` in `do_execveat_common`:** a boolean `is_su_session` starts false. It skips hooks for `susfs_is_current_proc_no_su()`; requires `ksu_su_compat_enabled` and branches by the SD-card-decryption static key between `ksu_handle_execveat()` and `ksu_handle_execveat_sucompat()`; interprets **zero** return as `is_su_session=true`. This runs before the original process-limit check. The current Rothko candidate is **NOT equivalent**: it invokes the pershoot prehook after the process-limit check and propagates negative results to `out_ret`, with no session bool/static-key/no-su selection. Crucially, pinned pershoot `ksu_handle_execveat_sucompat()` returns **0 on unrelated filenames, chroot denial and UID denial as well as its success path**. Thus `!ret` on the pershoot provider **cannot identify an authenticated SU session**. The official companion implementation uses distinct nonzero rejection results; adapting its caller naively is unsafe.
- **Hunk 4 — `@@ -1980,6 +2012,10 @@`:** after `bprm_execve`, conditionally invokes `ksu_handle_post_execveat_sucompat(..., &retval)` if `is_su_session`. The *original-KernelSU companion* defines a callback that checks `*retval >= 0` before calling `ksu_install_su_fd()`, but its return is discarded at the caller. This callback is **not available in pinned pershoot**. Existing KSUN generic `ksu_install_fd` or separate sulog FD must not be treated as that privileged authenticated SU session FD. Neither the current typed prehook patch nor previous green source-only CI covers this post-exec behavior.
- **Additional hazards:** The exact companion changes pathname bytes via `memcpy((void *)filename->name, ksud_path, sizeof(ksud_path))`; our selected pershoot fail-closed chain instead uses allocated replacement and `putname()`. Avoid importing its unsafe pathname ownership and no-abort cases. `susfs_is_current_proc_no_su()` in pinned `susfs_def.h` tests `TIF_PROC_NO_SU`; ARM64/vendor bit collision remains unreviewed. The source-only CI [38561088239](https://github.com/cogan17/Xiomi-14t-pro/actions/runs/38561088239) proves just **existing include + typed prehook structural composition**, not official four-hunk semantic parity, effective linking or runtime.

**Provider-selection decision:** `scripts/rothko_install_root_driver.py` and `.github/workflows/rothko-root-integration.yml` intentionally retain official vanilla `KernelSU-Next@02a9e1c5fb2c4fd8117429fe004136332788c1b6` for non-SUSFS root integration. That source has no matching pinned pershoot prehook symbol. The SUSFS audit pin `pershoot/KernelSU-Next@3438d6aa431f96a23f9e625bec3d53ce1fb14161` has the prehook but lacks the official posthook. **Do not change the vanilla installer pin or add an unvalidated SUSFS mode yet.** An eventual dedicated `SUSFS` route must explicitly verify exact remote+SHA, `CONFIG_KSU=y`, `KSU_SUSFS` built-in with SUSFS core/header manifest, `feature/sucompat.o` provider selection, complete entry/post/FD contract, and rejection of mixed roots before one checked temporary source integration.

**Next single actionable gate:** design and source-check a **fail-closed SUSFS-specific provider selection contract**, without changing default vanilla installer behavior or creating a build/flash artifact. A separate post-exec FD design must first fix false session detection and verify successful exec/ownership, UID/domain, rollback and cleanup. No KMI/build/merge/flash approval.

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


## Verified upstream header provenance — CI run 38324010643

The successful read-only `context-drift` job fetched and verified the pinned SUSFS commit/tree and reported `kernel_patches/include/linux/susfs_def.h` in the upstream tree. The official Android 14 / Linux 6.1 patch references `#include <linux/susfs_def.h>` in fifteen added lines (patch lines 52, 124, 566, 900, 1021, 1082, 1164, 1263, 1399, 1641, 1903, 2035, 2143, 2192, 2320). Five inspected conflict-sensitive hunks require semantic review and the directive was absent in their pristine BSP targets.

**Disposition:** header location is verified, but presence is not proof that all companion headers, implementation sources, configuration symbols, exports and include paths are integrated. Do not copy this header alone or auto-apply mixed hunks. Next source-only task: build an exact pinned-tree dependency manifest for `susfs_def.h` and map its referenced types/functions to the BSP before creating the first isolated port candidate.

The same run's `provenance` job deliberately failed with exit code 14 on the official patch applicability and security gates; `context-drift` succeeded. This is expected and must remain release-blocking.


## Patch failure triage — latest observed run 38324521235

- `provenance`: failure (expected release gate, exit 14); `context-drift`: success; `gitlab-transport`: skipped on automatic run.
- `fs/proc/task_mmu.c` upstream hunk near 883 searches for a `mem_size_stats` / `vma_pages(vma)` block that differs in the target. The mismatch is not evidence that removing the VMA check is safe.
- `mm/memory.c` upstream hunk near 79 searches for an include sequence involving `linux/vmalloc.h`, `linux/sched/sysctl.h`, `linux/set_memory.h`, `trace/events/kmem.h`, and `trace/hooks/mm.h`. Reconcile the real target includes and symbol dependencies before modifying the file.
- Existing independent security blockers remain: credential/post-exec session FD, KSUN companion patch, execve/ARM64 source contract, and ARM64 TIF collision.

**Next implementable unit:** create a source-only dependency inventory for the pinned SUSFS header and the precise upstream/BSP functions touched by these two rejected hunks. Do not manufacture a hunk offset, remove a VMA condition, or treat header insertion as a complete port.
