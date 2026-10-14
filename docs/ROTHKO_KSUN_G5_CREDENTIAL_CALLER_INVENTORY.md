# KSUN G5 credential caller inventory (pinned upstream)

Pinned source: `pershoot/KernelSU-Next@3438d6aa431f96a23f9e625bec3d53ce1fb14161`. Source-only inspection; no kernel build or runtime verification.

| Path | Lines | Ownership / access |
| --- | --- | --- |
| `kernel/core/init.c` | 81, 135-136, 268 | Defines owner `ksu_cred`, prepares and releases it |
| `kernel/selinux/selinux.c` | 161-162 | Checks shared pointer and mutates its SELinux domain |
| `kernel/feature/sucompat.c` | 421, 461, 529 | Three `override_creds(ksu_cred)` readers; matching revert paths at 428/432, 468/472, 531 |
| `kernel/feature/kernel_umount.c` | 116 | One override reader; revert at 126 |
| `kernel/policy/allowlist.c` | 425 | One override reader; revert at 456 |
| `kernel/runtime/ksud_integration.c` | 289 | One override reader; revert at 330; `loaded` latched before borrow |
| `kernel/infra/su_mount_ns.c` | 102, 176 | One `dentry_open` reader and one override reader; namespace helper returns to outer revert at 182 |
| `kernel/include/ksu.h` | declaration | Public `extern struct cred *ksu_cred` must be retired as a consumer API |

**Corrected count (2026-10-14):** seven direct override readers across five source files, plus the shared-credential `dentry_open` in namespace setup. The earlier six-reader count omitted `su_mount_ns.c`; do not reuse it as a complete inventory. `kernel/hook/setuid_hook.c:31` also has an unused extern declaration. This is not an audit of all kernel credential operations.

The isolated 16-stage composition in `tests/test_rothko_ksun_g5_composition.py` migrates all seven overrides and the namespace open. Source-only apply/reverse and guard tests passed; module lifetime, postcommit namespace failure and runtime remain blocked. Existing candidate artifacts are preserved.

## Mandatory migration sequence

1. Add a single shared credential manager with private owner pointer, synchronization, explicit READY state, and a borrow/release interface. Keep the pointer unpublished until SELinux initialization succeeds.
2. Replace **all seven** direct overrides and the namespace open with checked borrow, override, revert and put; preserve every existing error/cleanup path. Never acquire `get_cred` after dropping the lock guarding teardown.
3. Convert the owner init/exit and SELinux setup to the same manager. Atomically stop new borrowing before owner put, then quiesce callback/workqueue paths.
4. Move one-shot latches after borrow/readiness checks; reject failed setup and late-load escape.
5. Add host-only negative tests for concurrent borrow vs teardown, duplicate setup, error unwinds and all seven override sites plus namespace open. Run isolated applicability only after candidate patches are generated in actual prior-patch order.

**Not approved:** isolated `get_cred(ksu_cred)` insertion, NULL checks without locking, automatic kernel builds, merging Draft PR #9, release or flashing. G1 patch-apply CI green does not prove G5 runtime safety.
