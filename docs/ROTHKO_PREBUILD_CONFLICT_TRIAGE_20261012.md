# Rothko KSUN + SUSFS — prebuild conflict triage (2026-10-12)

Scope: only `cogan17/Xiomi-14t-pro` Draft PR #9; BakaSU out of scope. **Do not compile, merge or flash yet.**

## Evidence
- Audit run [38241854970](https://github.com/cogan17/Xiomi-14t-pro/actions/runs/38241854970), job 114786153381, completed **failure** with exit code 6 after read-only `git apply --check --verbose`.
- Five rejected patch targets confirmed: `fs/exec.c` (context line 64), `fs/namei.c` (hunk around `lookup_one_qstr_excl`, line 1614), `fs/proc/base.c`, `fs/proc/task_mmu.c`, `mm/memory.c` (context line 79).
- `security/selinux/avc.c` and `security/selinux/selinuxfs.c` were checked; several SELinux hooks applied with offsets in dry run. **A matching patch context does not prove semantic compatibility.**
- Latest audit run [38243847508](https://github.com/cogan17/Xiomi-14t-pro/actions/runs/38243847508) was still **in progress** when checked. It may fail early if SUSFS `gki-android14-6.1` branch HEAD differs from pinned `5192aa2d33b381b58c1051532f9e1dfa5de6e8d3`. Do not infer a result until jobs complete.
- Pinned KSUN `3438d6aa431f96a23f9e625bec3d53ce1fb14161` and SUSFS `5192aa2d33b381b58c1051532f9e1dfa5de6e8d3`.

## Findings requiring semantic review
1. **Execve**: KSUN `syscall_event_bridge.c` uses the `pt_regs` sucompat path; SUSFS kernel patch expects `fd/filename` and `ksu_handle_post_execveat_sucompat`. Resolve hook ownership, compile-time variants and pre/post execution ordering. Do not install duplicate hooks.
2. **ARM64 flags**: SUSFS defines `TIF_PROC_NO_SU 34`; pinned Rothko baseline did not show the symbol. Verify that flag index 34 is valid in Rothko's `thread_info` flag storage, not reserved/used by another feature, and whether thread-flag helpers accept it. Do not simply add a define.
3. **SELinux**: KSUN already implements `selinux_hide.c`. Check `avc_has_perm` signatures, existing vendor hooks, and upstream SUSFS changes in `avc.c`, `hooks.c`, `selinuxfs.c` for semantic overlap.
4. **BSP patch conflicts**: resolve the five rejected hunks against exact Rothko functions. Distinguish changed context from actual logic changes and test independently in an isolated worktree.
5. **Pinning**: keep the KSUN and SUSFS source SHAs fixed and review upstream changes separately; never auto-follow a moving branch without audit.

## Required prebuild acceptance
- Verified pinned source acquisition, patch provenance and hashes.
- No missing or duplicate execve/post-execve symbols, no duplicate SELinux hook ownership.
- No conflicting ARM64 thread flags or KMI/ABI breakage.
- Five rejected hunks manually adapted with source-level reasoning, static checks and `git apply --check` or equivalent isolated checks passing.
- A green dedicated compatibility audit and explicit review of its logs; **green documentation guard alone is insufficient**.
- Keep Draft PR #9 unmerged until all gates pass; actual boot stability requires device testing later.

This document is a reproducible investigation handoff, not a claim that integration is complete.
