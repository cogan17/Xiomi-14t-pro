# Rothko KSUN + SUSFS: five rejected patch targets

Status: **investigation only**. No source changes or builds. Baseline: `dev/rothko` (Xiaomi BSP 6.1.57). SUSFS: official Simonpunk `gki-android14-6.1` commit `5192aa2d33b381b58c1051532f9e1dfa5de6e8d3`. KSUN: `3438d6aa431f96a23f9e625bec3d53ce1fb14161`.

Evidence: [GitHub Actions run 38236950368](https://github.com/cogan17/Xiomi-14t-pro/actions/runs/38236950368), job 114769847590. `git apply --check --verbose` exited 6; patch was not applied. These are *five file-level rejects*, not necessarily five hunks.

| File | First rejected patch location | Verified BSP source landmarks | Next review |
| --- | --- | --- | --- |
| `fs/exec.c` | 64 | `linux/binfmts.h` line 47; `bprm_execve` near 1805/1948; `do_execveat_common` near 2022 | Compare include context and process-exec hook placement; retain Xiaomi exec hooks. |
| `fs/namei.c` | 1614 | `path_lookupat` near 2462; `filename_lookup` near 2593; `do_filp_open` near 3733 | Compare path-walk and lookup hook semantics, not just hunk offsets. |
| `fs/proc/base.c` | 100 | `trace/hooks/sched.h` line 101; `proc_pid_status` near 3260 | Preserve vendor proc/trace hooks and proc visibility behavior. |
| `fs/proc/task_mmu.c` | 883 | `show_smap` near 864; `memset(&mss` near 872 and 914 | Compare VMA accounting and smaps logic, including vendor changes. |
| `mm/memory.c` | 79 | `linux/vmalloc.h` line 78; `handle_mm_fault` near 5145 | Check include insertion and page-fault hooks against vendor MM changes. |

Line landmarks were read from `dev/rothko` through the GitHub repository connector. They **do not prove** any particular patch hunk is semantically portable. The exact patch additions/removals still need side-by-side review before authoring a Rothko-specific patch.

## Independent KSUN / SELinux gates

- The official SUSFS README warns that patches can differ even at the same kernel version and that its KernelSU patch targets official KernelSU revisions. Do **not** apply `kernel_patches/KernelSU/10_enable_susfs_for_ksu.patch` blindly to the pinned KSUN fork.
- Compare SELinux hide implementation, security hooks and root authorization behavior against pinned KSUN; check duplicate inline hooks, command dispatch, and ownership of each hook.
- Confirm `TIF_PROC_NO_SU` bit allocation in the actual Rothko arm64 thread-info and its usage across vendor code; never invent or alias a flag.
- Confirm structures, SUSFS user/kernel command IDs and all 16 dispatcher call signatures against the pinned sources.
- No forced patching, no kernel compile, no artifact/release, no flash. Keep PR Draft.
