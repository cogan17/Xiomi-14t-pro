# Rothko KSUN + SUSFS integration: implementation gates

Status: BLOCKED. This document records source facts and acceptance criteria; it does not authorize builds, merges, or flashing.

## Pinned inputs
- Rothko BSP: `dev/rothko` (Linux 6.1.57), working branch `feat/rothko-ksun-susfs-compat-audit`.
- KernelSU-Next: `pershoot/KernelSU-Next@3438d6aa431f96a23f9e625bec3d53ce1fb14161`.
- SUSFS: `simonpunk/susfs4ksu@5192aa2d33b381b58c1051532f9e1dfa5de6e8d3`, branch `gki-android14-6.1`.
- Do not substitute an unverified mirror. An alternative source must yield the identical Git commit and tree, and required file hashes must be recorded. Network failures must remain failures.

## Verified Rothko exec path
- `fs/exec.c:bprm_execve()` calls `exec_binprm(bprm)`; negative results take the error path. The success path clears `current->in_execve`, calls `rseq_execve()`, updates accounting and returns.
- `fs/exec.c:do_execveat_common()` calls `bprm_execve()`, then `free_bprm()` and `putname()`.
- `exec_binprm()` handles interpreter transitions and emits the successful exec trace. A post-exec hook must not run on unsuccessful exec or accidentally run on every unrelated process.
- These facts establish potential call sites only; no session FD authorization is established.

## Pinned KSUN privilege flow
- `kernel/feature/sucompat.c:ksu_handle_execveat_sucompat()` checks chroot and UID allowlist before calling `escape_with_root_profile()`.
- Pinned upstream rewrites `filename->name` with `ksud_path` before checking privilege-escape success. The candidate patch moves the rewrite after the check.
- `kernel/policy/app_profile.c:escape_with_root_profile()` can reach `out_abort_creds` with `ret == 0` without committing credentials (already privileged / disable-escape cases). A return value of zero alone is NOT proof of a new privileged session.
- The candidate patch propagates the result of `set_cred_ucounts()`; it has not been compiled or linked.
- The writable capacity and ownership of `filename->name` must be proven before any `memcpy` path can be approved.

## Required post-exec / session FD contract
1. Identify a genuine pinned-KSUN authorization/session state and how it survives `execve`; reject a new global boolean or unconditional post-exec installer.
2. Define the post-exec hook in the same configuration matrix in which `fs/exec.c` calls it; verify declaration, object inclusion, and link visibility.
3. Require a successful exec, an authorized and still-live session, and a current credential/security-domain match before FD installation.
4. Specify descriptor ownership, `CLOEXEC` behavior, lifetime, release callback, fork/exec inheritance, cancellation, and cleanup on all error paths.
5. Prove that repeated execs, failed execs, UID changes, chroot, and denied escalation cannot leak or install session FDs.
6. Port all rejected SUSFS 6.1 hunks against Rothko semantics, not just matching line context; review `TIF_PROC_NO_SU` bit 34 collision separately.
7. Only after the source contracts are implemented: run patch applicability, compile and link checks, then controlled runtime validation. A successful compile is not flashing approval.

## Current blockers
- GitLab intermittently refuses the pinned SUSFS fetch.
- Official SUSFS KSUN companion patch does not apply cleanly to the pinned KSUN.
- Pinned KSUN has no verified `ksu_handle_post_execveat_sucompat()` and session-FD installer implementation.
- Official SUSFS 6.1 patch rejects `fs/exec.c`, `fs/namei.c`, `fs/proc/base.c`, `fs/proc/task_mmu.c`, and `mm/memory.c`.
- No compilation, linking, or runtime safety proof.

Do not mark the compatibility gate green or merge PR #9 while any blocker remains.
