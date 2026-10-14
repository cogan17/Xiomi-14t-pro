# KSUN G5 shared credential lifetime contract — source-only design

Status: **BLOCKED / design candidate, not implementation approval**. No build, flash, release or PR merge authorized.

## Verified upstream anchors
- Pin: `pershoot/KernelSU-Next@3438d6aa431f96a23f9e625bec3d53ce1fb14161`.
- Public declaration: `kernel/include/ksu.h` declares `extern struct cred *ksu_cred;` (NOT `kernel/ksu.h`).
- Owner: `kernel/core/init.c` defines `ksu_cred`, allocates with `prepare_creds()`, and calls `put_cred(ksu_cred)` on exit.
- Reader: `kernel/runtime/ksud_integration.c::load_module_rc_once()` sets `loaded = true` before readiness check, calls `override_creds(ksu_cred)`, then `revert_creds(old_cred)`. Other readers must be enumerated before implementation.
- Existing G1 source-only audit succeeded on commit `72f9f80ee9aea2ee2251df4a2011771ba5b27ae7`, runs [38489354797](https://github.com/cogan17/Xiomi-14t-pro/actions/runs/38489354797) and [38489350334](https://github.com/cogan17/Xiomi-14t-pro/actions/runs/38489350334). These do not prove concurrency safety.

## Required single-owner contract
1. **Ownership:** store the owner credential reference in a private manager; do not expose a mutable global pointer as the borrow interface. All callers must be migrated, including sucompat, allowlist, kernel umount and runtime module rc.
2. **Publication:** only publish READY after SELinux domain initialization and verification succeed; reject duplicate or late setup and preserve explicit failure state.
3. **Borrow:** acquire a reference while holding the SAME synchronization protecting READY and pointer invalidation; use `get_cred()` only while the pointer is known alive. Release lock before sleepable operations. A NULL check followed by `get_cred()` outside the lock is unsafe.
4. **Use:** only on a successfully borrowed credential: `old = override_creds(borrowed)`; after every path, `revert_creds(old)` and `put_cred(borrowed)`. Borrow failure must not set one-shot `loaded` / `rc_hooked` flags.
5. **Teardown:** atomically clear READY and unpublish the pointer under the same lock, release lock, quiesce all callbacks/workqueues that can borrow, then release the owner reference. Existing borrowed references may finish safely; do not hold a spinlock across `override_creds` or file IO.
6. **Lifecycle:** validate builtin versus module semantics, repeated init/exit, late-load setup, and lock initialization. Prevent use of the manager after teardown.
7. **Error handling:** no success path if setup failed; late-load must not escape to root with a failed shared-credential domain transition.
8. **FD boundary:** SU_SESSION post-exec task/owner/revocation remains an independent blocker, not implicitly solved by credential borrowing.

## Acceptance gates before implementation can be promoted
- Map every global `ksu_cred` reader/writer and all `override_creds` call sites in the pinned source; no bypass of borrow API.
- Add host-only state-machine tests for UNINITIALIZED, PREPARED, READY, FAILED, STOPPING, STOPPED; race scenarios for borrow vs teardown; and negative tests for premature one-shot latch.
- Generate candidate patch against exact upstream source and preceding patch sequence; verify forward/reverse applicability in CI without compiling.
- Compile/link, ABI/KMI, runtime and flashing remain BLOCKED under BUILD HOLD.

## Resume instruction
Do not repeat prior G1 patch-format experiments. Next perform complete caller inventory and introduce a single fail-closed borrow API candidate; do not mark the kernel flashable.
