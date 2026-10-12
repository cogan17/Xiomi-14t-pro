# Rothko KSUN/SUSFS post-execve control-flow audit (2026-10-12)

**Disposition: BLOCKED — do not compile, merge or flash.** This is a source-level control-flow analysis, not a successful integration test.

## Exact source under review

- KSUN: `pershoot/KernelSU-Next@3438d6aa431f96a23f9e625bec3d53ce1fb14161`.
- SUSFS: `simonpunk/susfs4ksu gki-android14-6.1@5192aa2d33b381b58c1051532f9e1dfa5de6e8d3`.
- Rothko BSP: `dev/rothko` (Linux 6.1.57); proposed changes live on `feat/rothko-ksun-susfs-compat-audit`.

## Verified pinned KSUN control flow

1. `kernel/feature/sucompat.c` has an `#ifdef CONFIG_KSU_SUSFS` branch with `int ksu_handle_execveat_sucompat(int *fd, struct filename **filename_ptr, void *argv_user, void *envp_user, int *flags)`, called by `ksu_handle_execveat`. The same file has a separate `#if defined(CONFIG_KPROBES) && !defined(CONFIG_KSU_SUSFS)` branch implementing `long ksu_handle_execveat_sucompat(const char __user **filename_user, int orig_nr, struct pt_regs *regs)`. These are **mutually exclusive compile-time interfaces**, not overloads.
2. `kernel/hook/syscall_event_bridge.c` calls the **pt_regs** variant from `ksu_hook_execve_common`, conditional on `ksu_su_compat_enabled`. Verify the bridge's build/Kconfig inclusion before enabling SUSFS: compiling that bridge with the SUSFS branch's header declarations would create a type/signature mismatch.
3. In the SUSFS branch, `ksu_handle_execveat_init` sets the no-su process marker for selected init descendants via `susfs_set_current_proc_no_su()`, and checks `susfs_is_current_proc_no_su()`. The marker's lifetime, inheritance and clear-on-exec behavior require inspection of the SUSFS kernel patch.
4. No `ksu_handle_post_execveat_sucompat` declaration or definition exists in the inspected pinned KSUN `sucompat.c`, `sucompat.h`, or bridge. The SUSFS kernel patch refers to that symbol. It is **not safe to add a no-op stub** to satisfy the build.
5. `ksu_su_compat_enabled` is already defined in pinned KSUN. Companion patch changes must not duplicate it.

## Rothko execution lifecycle

In Rothko `fs/exec.c`, `exec_binprm()` loops through `search_binary_handler()`, including interpreter rewrites. Only after successful completion does it execute `audit_bprm`, `trace_sched_process_exec`, `ptrace_event`, and `proc_exec_connector` before returning 0. A post-execve hook must not run on failed exec attempts or intermediate interpreter iterations. The exact SUSFS companion patch's call site, arguments and intended semantics must be inspected before choosing an insertion point.

## Mandatory implementation conditions

- Obtain and review **both** pinned SUSFS patches: `kernel_patches/50_add_susfs_in_gki-android14-6.1.patch` and `kernel_patches/KernelSU/10_enable_susfs_for_ksu.patch`, especially the definition and invocation of `ksu_handle_post_execveat_sucompat`.
- Determine which KSUN hook implementation is compiled under the target `CONFIG_KSU_SUSFS`, `CONFIG_KPROBES`, and bridge build rules; prevent mixing incompatible signatures.
- Define post-execve behavior from the upstream companion implementation rather than guessing its signature or inventing a stub.
- Confirm the marker is set, inherited, and cleared only as intended; ensure failed execs and interpreter rewrites cannot silently alter privilege eligibility.
- Port rejected SUSFS hunks against Rothko's actual BSP code with review of each hunk, SELinux, and ABI/KMI consequences.
- Validate compile-time prototypes and linking, then CI build, then device-side behavior separately. **A successful source gate alone is not a boot-safety guarantee.**

## Current result

**Not compatible yet.** This audit records concrete incompatible interfaces and the exact missing dependency. Do not bypass a failing source gate or claim completion based on the presence of a symbol.
