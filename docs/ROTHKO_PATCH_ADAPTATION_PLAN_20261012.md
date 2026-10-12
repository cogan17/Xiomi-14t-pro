# Rothko KSUN/SUSFS — five-file patch adaptation plan

Scope: Draft PR #9 only. Read-only analysis; no build, merge or flash.

## Work order
1. `fs/exec.c`: compare exact upstream hunk around line 64 with Rothko includes and execve call chain. Confirm whether the KSUN pt_regs bridge already owns the hook and whether SUSFS expects a second pre/post hook. **Do not add duplicate execve calls**.
2. `fs/namei.c`: compare `lookup_one_qstr_excl` function and surrounding dentry lifetime. Reject purely mechanical patch if return path or refcount semantics changed.
3. `fs/proc/base.c`: inspect `/proc` inode, path, and visibility changes; verify vendor guards and relevant config macros before porting.
4. `fs/proc/task_mmu.c`: inspect VMA/map reporting modifications, mmap locking, and compat handling; avoid stale assumptions about VMA iteration.
5. `mm/memory.c`: inspect exact upstream hunk around line 79 and current Rothko include/hook locations; do not insert duplicate mm hooks.

## Independent compatibility gates
- Compare both pinned upstream source commits and record provenance.
- Validate `TIF_PROC_NO_SU` bit 34 against Rothko arm64 `thread_info`, `_TIF_WORK_MASK`, and other assigned flags.
- Verify KSUN `ksu_handle_execveat_sucompat` compile-time variants and missing `ksu_handle_post_execveat_sucompat` symbol before porting SUSFS hook.
- Inspect SELinux hook ownership and `avc_has_perm` signature; no duplicate KSUN/SUSFS hide logic.
- Adapt patches as small, isolated commits with independent tests; do not force apply with fuzz or `--reject`.
- Re-run source audit and check full CI logs; keep PR Draft until all checks pass.

## CI snapshot
- Earlier audit run `38241854970` failed `git apply --check` with five rejected files.
- Run `38243847508` was still in progress when last inspected; its outcome must be checked, not assumed.

No assertion of build readiness or boot stability.
