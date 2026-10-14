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
| `kernel/include/ksu.h` | declaration | Public `extern struct cred *ksu_cred` must be retired as a consumer API |

**Count:** six direct override readers across four source files. The count excludes other credential handling APIs and must not be represented as a complete audit of all kernel credential operations.

## Mandatory migration sequence

1. Add a single shared credential manager with private owner pointer, synchronization, explicit READY state, and a borrow/release interface. Keep the pointer unpublished until SELinux initialization succeeds.
2. Replace **all six** direct overrides with checked borrow, override, revert and put; preserve every existing error/cleanup path. Never acquire `get_cred` after dropping the lock guarding teardown.
3. Convert the owner init/exit and SELinux setup to the same manager. Atomically stop new borrowing before owner put, then quiesce callback/workqueue paths.
4. Move one-shot latches after borrow/readiness checks; reject failed setup and late-load escape.
5. Add host-only negative tests for concurrent borrow vs teardown, duplicate setup, error unwinds and all six call sites. Run isolated applicability only after candidate patches are generated in actual prior-patch order.

**Not approved:** isolated `get_cred(ksu_cred)` insertion, NULL checks without locking, automatic kernel builds, merging Draft PR #9, release or flashing. G1 patch-apply CI green does not prove G5 runtime safety.
