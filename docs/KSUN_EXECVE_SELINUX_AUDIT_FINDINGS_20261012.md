# KSUN + SUSFS Rothko — RESUMED, execve/SELinux findings

**Resumed by owner on 2026-10-12.** This supersedes the earlier KSUN HOLD instruction for this repository only. Scope: `cogan17/Xiomi-14t-pro`, Draft PR #9. The separate BakaSU repository remains out of scope and must not be modified.

## Source pins and evidence
- Rothko baseline `dev/rothko`, Linux 6.1.57 BSP.
- KSUN `pershoot/KernelSU-Next@3438d6aa431f96a23f9e625bec3d53ce1fb14161`.
- Simonpunk SUSFS `gki-android14-6.1@5192aa2d33b381b58c1051532f9e1dfa5de6e8d3`.
- Source-audit run `38241854970`, job `114786153381`, **failure** (existing patch applicability conflicts); read-only symbol scan completed and printed its results. Earlier five rejected BSP patch targets remain open.

## Verified source findings from audit log
1. KSUN `kernel/feature/sucompat.h:27` declares `long ksu_handle_execveat_sucompat(const char __user **filename_user, int orig_nr, struct pt_regs *regs)`; KSUN `kernel/feature/sucompat.c:224` additionally defines an `int` fd/filename variant and at :581 a `long` pt_regs variant. KSUN `kernel/hook/syscall_event_bridge.c:103` calls the pt_regs form. **Investigate conditional compilation and hook ownership before integrating the upstream kernel execve hunk.**
2. KSUN pinned source scan found **zero** occurrences of `ksu_handle_post_execveat_sucompat`; SUSFS kernel patch expects it and its KernelSU companion patch adds it. **The official kernel patch cannot link against pinned KSUN unchanged.**
3. `ksu_su_compat_enabled` is already a static key in KSUN `kernel/feature/sucompat.c:51`; SUSFS companion patch also changes this symbol. Avoid duplicate definitions.
4. KSUN calls `susfs_is_current_proc_no_su` in `kernel/feature/sucompat.c:197` and `kernel/supercall/dispatch.c:478`. SUSFS defines it in `include/linux/susfs_def.h:137`; the SUSFS header defines `TIF_PROC_NO_SU 34` at :65. Rothko baseline symbol scan returned no occurrences of `TIF_PROC_NO_SU`. Validate bit 34 against arm64 thread flags and `_TIF_WORK_MASK`/thread-info storage before any insertion.
5. KSUN already has `kernel/feature/selinux_hide.c`, using `avc_has_perm` in multiple locations. Official SUSFS patch also changes `security/selinux/{avc.c,hooks.c,selinuxfs.c}`. **SELinux hide ownership and API compatibility unresolved.**

## Next implementation gates
- Read full `sucompat.c`, `sucompat.h`, `syscall_event_bridge.c`, `selinux_hide.c` at pinned KSUN SHA; enumerate CONFIG gates and active hook paths.
- Compare official SUSFS `KernelSU/10_enable_susfs_for_ksu.patch` with KSUN pinned source, including the missing post-execve function and SELinux changes.
- Inspect Rothko arm64 thread_info and SELinux hooks for signature, ABI/KMI, and vendor modifications.
- Author narrow, reviewed compatibility adaptations in this branch, with source/static tests before any kernel build. Keep PR #9 Draft until gates pass. No forced patch, merge, release, or flashing.

This document records verified source facts, not proof of compatibility or successful build.
