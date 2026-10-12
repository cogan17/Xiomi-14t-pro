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


### Source-level permission/FD boundary audit (2026-10-12)

Scope: independent, read-only review of pinned `pershoot/KernelSU-Next@3438d6aa431f96a23f9e625bec3d53ce1fb14161`, plus the four candidate patches applied sequentially only to the temporary GitHub Actions checkout. No Rothko BSP compilation or patch integration. Additional audit: `scripts/rothko_ksun_security_contract.py`, invoked by `.github/workflows/rothko-ksun-candidate-audit.yml`. **A green audit means expected source structures were observed, not that root authorization or a flashable kernel was approved.**

**Verified entry-point checks (scoped, not universal):**
- `kernel/feature/sucompat.c:ksu_handle_execveat_sucompat` checks `current_chrooted()` and `ksu_is_allow_uid_for_current(current_uid().val)` before calling `escape_with_root_profile()`. This only covers the inspected SUSFS-style `su` path.
- `kernel/supercall/perm.c:allowed_for_su` permits manager identity or a currently allowed UID. In `kernel/supercall/dispatch.c`, the `KSU_IOCTL_GRANT_ROOT` entry maps to `allowed_for_su`, and `ksu_supercall_handle_ioctl()` executes a command-specific permission check. It is incorrect to say this particular root-grant ioctl has no permission gate.
- `kernel/policy/allowlist.c:__ksu_is_allow_uid_for_current` treats UID 0 specially by checking the KSU security domain, and the allowlist distinguishes manager/shell/allowed profiles. `ksu_get_root_profile()` chooses a profile (including default fallback); **profile selection is not itself a permission decision**. All callers and build-config alternatives still require review.

**FD finding — distinguish two different contracts:**
- `kernel/supercall/supercall.c:ksu_install_fd()` already allocates an anonymous `ksu_driver` FD with `O_CLOEXEC`. Under `CONFIG_KSU_SUSFS`, `ksu_supercall_reboot_handler()` schedules its installation via `task_work_add(..., TWA_RESUME)`.
- Its `anon_ksu_ioctl` delegates to `ksu_supercall_handle_ioctl`, which checks individual ioctl permissions. `kernel/sulog/fd.c` also implements a **separate log FD**, not a substitute for the privileged driver/session contract.
- `O_CLOEXEC` closes a previously installed descriptor on successful exec. The reboot/task-work installer does **not** prove an authenticated *post-exec* FD installation after a successful `execve`. The SUSFS kernel patch refers to `ksu_handle_post_execveat_sucompat`; this was not found in inspected pinned KSUN `sucompat.c` or the syscall bridge. Never replace the missing hook with a no-op or automatically install an ioctl-capable FD on every exec.
- Remaining required proof: trusted session origin, UID/security-domain binding, successful-exec-only timing, installation and rollback order, fork inheritance, descriptor ownership/cleanup, repeated/denied exec behavior.

**Still-blocking candidate concerns:**
- The SELinux candidate returns errors from `setup_selinux` and aborts prepared credentials in `escape_with_root_profile` and `escape_to_root_for_init`. Yet `setup_ksu_cred()` **still only logs** a failed transition on `ksu_cred`; ownership and failure propagation of that separate state remain unresolved. The source audit checks that this blocker is still present.
- The groups and seccomp scratch candidates adjust ordering and error handling, but memory/lock/credential lifetime and ABI behavior against Rothko remain unproven. Do not infer runtime safety from substring checks.
- No universal pre-commit authorization proof, post-exec session mechanism, linking test, device ABI/KMI gate, or boot validation exists.

**Gate disposition: BLOCKED.** Do not merge Draft PR #9, enable the suspended GitLab source job, publish artifacts, or flash. Unexpected changes in the pinned-source patterns must fail the source-evidence audit instead of silently marking a release compatible.


### Negative regression gate for source audit (2026-10-12)

To prevent a false green result caused by matching an unrelated function, the SUSFS sucompat UID/chroot preconditions and replacement-file checks are now scoped to the actual `ksu_handle_execveat_sucompat(int *fd, ...)` handler in `scripts/rothko_ksun_security_contract.py` (commit `789309a`). The checks are intentionally structural and do **not** establish runtime permission integrity.

CI runs `tests/test_rothko_ksun_security_contract.py` against a **temporary copy of only the eight pinned KSUN source files**. Its nine negative cases intentionally remove or bypass an observed guard and require the validator to return nonzero with a `REVIEW REQUIRED` indication:
1. su UID allowlist check;
2. su chroot check;
3. su filename redirection assignment;
4. `GRANT_ROOT` ioctl permission mapping;
5. per-ioctl permission invocation;
6. root-profile SELinux error propagation;
7. init SELinux failure handling;
8. anonymous driver FD `O_CLOEXEC`;
9. `setup_ksu_cred` SELinux failure observation.

A passing mutation suite indicates only that **these exact regressions are detected by the static validator**. It is not a proof of complete control-flow dominance, hook authorization, Kconfig compatibility, FD lifecycle or kernel safety. The reported `setup_ksu_cred` path still merely logs failures. The seccomp candidate also requires review of task-state changes between preallocation and credential commit, plus real kernel seccomp locking semantics.

No kernel compilation, GitLab fetching, changes to Rothko BSP, artifact creation, merge, release or flashing are performed by this suite. **PR #9 remains Draft; RELEASE BLOCKED.**


### Pinned ioctl permission matrix — source audit only (2026-10-12)

Source: `pershoot/KernelSU-Next@3438d6aa431f96a23f9e625bec3d53ce1fb14161`, `kernel/supercall/dispatch.c`, `kernel/supercall/perm.c`, `kernel/supercall/supercall.c`. An ioctl-capable anonymous `ksu_driver` FD exists and uses `O_CLOEXEC`; per-command permission checks still apply independently. A reachable FD is **not proof of a privileged session or an unconditional root grant**.

The new `scripts/rothko_ksun_ioctl_matrix.py` pins the exact permission class for **all 26 known ioctl commands** in this KSUN snapshot, including:
- `GRANT_ROOT` → `allowed_for_su` (manager or allowlisted UID);
- `SET_SEPOLICY` and `GET_SULOG_FD` → `only_root`;
- `GET_APP_PROFILE` / `SET_APP_PROFILE` → `only_manager`;
- `SET_FEATURE` / `GET_WRAPPER_FD` → `manager_or_root`;
- `GET_INFO` and `GET_INFO_LEGACY` → `always_allow` (intentional upstream snapshot).

The complete table is checked for unexpected additions/deletions and permission-class changes. The audit also checks the definitions of all five permission helpers, and that `ksu_supercall_handle_ioctl` checks permission **before** dispatch. `tests/test_rothko_ksun_ioctl_matrix.py` injects **12 negative permission mutations** into a temporary copy of `supercall/{dispatch,perm}.c`; all must be rejected.

**Important security boundary:** In the pinned upstream, `only_root()` means `current_uid().val == 0`; it does **not** itself establish the KernelSU SELinux domain. Changing this guard, adding a privileged ioctl, or assuming all root processes belong to a KSUN-authenticated session requires separate review. The manager/allowlist checks restrict `GRANT_ROOT`, but do not establish a persistent authenticated post-`execve` session. Avoid conflating the existing reboot/task-work FD installer with the missing SUSFS post-execve contract.

**Gate: BLOCKED.** A successful matrix or mutation test confirms only an unchanged source-permission snapshot and test sensitivity, not the absence of other vulnerabilities, the safety of post-credential-commit operations, or ROM ABI/KMI/boot compatibility. No code from this track is included in the live Rothko BSP; no build, merge, release or flashing authorization is given.


### Shared ksu_cred provenance and lifetime — pinned-source audit (2026-10-12)

**Source evidence.** In pinned `pershoot/KernelSU-Next@3438d6aa431f96a23f9e625bec3d53ce1fb14161`, `kernel/core/init.c` creates the global `ksu_cred = prepare_creds()` and releases it at module exit via `put_cred(ksu_cred)`. The candidate `kernel/selinux/selinux.c:setup_ksu_cred()` still returns `void` and **only logs a failed** `setup_selinux(KERNEL_SU_CONTEXT, ksu_cred)`; there is no status for callers to check.

Two classes of consumers must be reconciled before any production patch:
- **Late load:** `kernelsu_init()` calls `setup_ksu_cred()` and then `escape_to_root_for_init()`, without checking a setup status or using the latter's return. Follow-on allowlist/hooks/observer initialization therefore cannot treat an attempted SELinux transition as proof of success.
- **Exec-triggered startup:** `runtime/ksud_integration.c` calls `setup_ksu_cred()` at init second stage on both CONFIG alternatives, and additionally at first zygote under `CONFIG_KSU_SUSFS`. The stage's `static_branch_disable` follows the void-return setup even if the SELinux transition failed. Review retry/one-shot semantics separately for both CONFIG branches; the non-SUSFS zygote path differs.
- **Later override:** `load_module_rc_once()` calls `override_creds(ksu_cred)` to access module RC data, then `revert_creds(old_cred)` on its cleanup paths. `override_creds` is a privileged credential swap, not a check that the stored credential has the expected KSU SELinux domain. The module RC loader also uses a one-shot `loaded` marker; its error/cancellation behavior requires explicit review.

**New reproducible evidence checks:** `scripts/rothko_ksun_shared_cred_audit.py` checks scoped source relationships in `core/init.c`, `runtime/ksud_integration.c`, `selinux/selinux.c` and `selinux/selinux.h` after the four existing candidate patches are applied in temporary CI source. `tests/test_rothko_ksun_shared_cred_audit.py` injects **11 negative mutations** involving allocation, stage setup/clearing, ignored SELinux failure, credential override, restoration, and destruction. The validator supports `--require-reviewed-remediation`, which must **exit nonzero** while the known shared-credential issues are present; negative tests require that denial. A passing source-evidence audit is not a successful remediation gate.

**Acceptance criteria for any future candidate** (still unimplemented):
1. Define a checked SELinux transition/status for the shared cred and propagate failures to **every** late-load and exec-stage caller, including both CONFIG paths.
2. Prove safe ownership and concurrency of `ksu_cred`; never publish, consume or override a credential with unverified domain. Audit init/unload ordering, refcounting and workqueue users.
3. Stop or safely retry one-shot stage transitions on failure, without disabling flags prematurely; do not add unconditional retries in exec hooks.
4. Define the failure behavior for late-load `escape_to_root_for_init`, follow-on hooks/allowlist, and loading `modules.rc`. Do not continue as though the root transition succeeded.
5. Audit `override_creds`/`revert_creds` across error exits; distinguish a valid shared credential from a token granting arbitrary new privileges. Verify against the actual Rothko BSP before any compiled test.

**Disposition: BLOCKED.** No kernel source change, merge, GitLab fetch, AK3/image, release or flashing follows from the successful structural tests. The authenticated post-exec session FD and existing SUSFS/BSP conflicts are *separate* unresolved blockers.
