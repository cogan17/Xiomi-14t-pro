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
- The candidate patch propagates the result of `set_cred_ucounts()` and **passes `git apply --check` against the pinned KSUN** in audit run 38253911159; it has not been compiled or linked.
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
- The pinned SUSFS fetch succeeded in audit run 38253911159 (commit verified); intermittent GitLab failures remain a reproducibility risk.
- Official SUSFS KSUN companion patch does not apply cleanly to the pinned KSUN.
- Pinned KSUN has no verified `ksu_handle_post_execveat_sucompat()` and session-FD installer implementation.
- Official SUSFS 6.1 patch rejects `fs/exec.c`, `fs/namei.c`, `fs/proc/base.c`, `fs/proc/task_mmu.c`, and `mm/memory.c`.
- No compilation, linking, or runtime safety proof.

Do not mark the compatibility gate green or merge PR #9 while any blocker remains.

## Audit evidence: 2026-10-12 run 38253911159
- Documentation Guard: PASS; source audit: FAIL (exit 14), correctly blocked.
- Pinned KSUN candidate: PASS `git apply --check`; this is patch applicability, not runtime authorization.
- Pinned SUSFS SHA: `5192aa2d33b381b58c1051532f9e1dfa5de6e8d3` resolved successfully.
- Companion patch: BLOCK; post-exec hook and session installer absent in pinned KSUN.
- Rothko patch conflicts: `fs/exec.c`, `fs/namei.c`, `fs/proc/base.c`, `fs/proc/task_mmu.c`, `mm/memory.c`.
- Next implementation gate: reconcile `fs/exec.c` call contract with a provable authorized session lifecycle, then port rejected hunks without bypassing fail-closed checks.

### KSUN seccomp pre-commit review (2026-10-12)

Pinned KSUN `kernel/policy/app_profile.c` currently calls `commit_creds(cred)` before `disable_seccomp()`. The latter allocates a full `task_struct` with `kmalloc(..., GFP_KERNEL)` and silently returns if allocation fails. Consequently, a successful `escape_with_root_profile()` may leave seccomp enabled after root credentials have already been committed. This is a **release-blocking partial-privilege state**, not fixed by the passing static candidate audit.

Required candidate design before enabling any integration: reserve the scratch task allocation **before** `commit_creds`; return `-ENOMEM` and abort prepared credentials if it fails; refactor seccomp cleanup to consume the preallocated scratch task without allocation after commit; ensure the scratch object is freed on all paths (including when seccomp was not enabled). Review locking and `seccomp_filter_release` behavior against the actual Rothko 6.1.57 BSP before approving this change. Also verify pre-commit SELinux/domain authorization and authenticated post-exec FD lifecycle. Do not treat a successful textual/patch-application audit as build, boot, or security approval.

### Additional credential-transition review (2026-10-12)

- Independent candidate audit run [38266926538](https://github.com/cogan17/Xiomi-14t-pro/actions/runs/38266926538) passed source ordering and patch application only.
- The pinned KSUN `escape_with_root_profile()` invokes `setup_selinux(profile->selinux_domain, cred)` before `commit_creds(cred)`, but the call has no checked return value. The same unchecked pattern exists in `escape_to_root_for_init()` with `KERNEL_SU_CONTEXT`. Confirm the actual helper declaration and its failure semantics before designing a fail-closed conversion; do not assume that changing the call site alone enforces authorization.
- `ksu_get_root_profile(cred->uid.val)` is a profile lookup, not by itself a proof of authorization to elevate. Verify upstream grant checks and entry-point trust boundaries, including SUSFS-specific hooks, before accepting the transition.
- Even with preallocated seccomp scratch, inspect task/seccomp state changes between preallocation and credential commit, and verify cleanup against Rothko BSP locking semantics.
- **Release gate remains blocked:** no verified pre-commit authorization, SELinux error propagation, authenticated post-exec FD lifecycle, or device build/boot proof. Keep PR #9 Draft and GitLab provenance on hold.

### Confirmed pinned KSUN SELinux helper contract (2026-10-12)

- Source: `pershoot/KernelSU-Next@3438d6aa431f96a23f9e625bec3d53ce1fb14161`, `kernel/selinux/selinux.h` declares `void setup_selinux(const char *, struct cred *);`.
- `kernel/selinux/selinux.c` implements it by calling `transive_to_domain(domain, cred, false)`; on nonzero return it logs `transive domain failed.` and returns **without propagating an error**.
- Consequently, `kernel/policy/app_profile.c` may continue to `commit_creds(cred)` after a failed SELinux domain transition, on both `escape_with_root_profile()` and `escape_to_root_for_init()`. This is a confirmed release blocker, not merely an unverified concern.
- A future candidate must change the helper contract to return an error, propagate it through **all callers** (including `setup_ksu_cred()` in `selinux.c`), and abort prepared credentials before commit. `setup_ksu_cred()` needs separate ownership/lifecycle review because it does not directly call `commit_creds()`.
- Do not merge, release, or flash based on a passing source-only audit.
