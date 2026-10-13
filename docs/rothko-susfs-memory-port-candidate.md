# SUSFS memory port candidate — isolated design, not applied

Source: `dev/rothko` BSP `b2d8b54a0d8bb002d32dda24e58d2b5d0423546b`, `mm/memory.c`. Evidence: [exact hunk comparison run 38328255916](https://github.com/cogan17/Xiomi-14t-pro/actions/runs/38328255916).

## Conflict A: include context

Upstream's first `mm/memory.c` hunk has **zero exact old-sequence matches**. Rothko's include block contains `linux/vmalloc.h` (L78), `linux/sched/sysctl.h` (L79), `linux/set_memory.h` (L80), and `trace/events/kmem.h` (L82), but not `trace/hooks/mm.h`. The upstream addition is a `CONFIG_KSU_SUSFS_SUS_MAP`-guarded `#include <linux/susfs_def.h>`.

**Candidate intent:** place the guarded SUSFS declaration only after confirming the pinned `susfs_def.h` is staged through the official dependency set and required symbols are defined. Do not introduce an unrelated `trace/hooks/mm.h` merely to force patch context to match.

## Conflict B: remote-memory access behavior

The other `mm/memory.c` hunk has **one exact old-sequence match** in the Rothko source around line 5854, but its addition is behavioral: a `CONFIG_KSU_SUSFS_SUS_MAP`-guarded test of `vma->vm_file` and `SUSFS_IS_INODE_SUS_MAP(file_inode(vma->vm_file))` that can break the transfer loop.

Rothko's surrounding code enters the loop after `vma_lookup` / optional `expand_stack` (L5844–5849), then calls `get_user_pages_remote` (L5857–5858). The VMA may be changed by that call; a safe implementation must review VMA lifetime, mmap locking, access control, and whether the upstream break is before or after page acquisition. A text match does **not** establish these semantics.

**Candidate intent:** isolate the guard placement and exact behavior for source review; do not alter the loop, error handling, or lock lifetime until the relevant contracts are proved.

## Acceptance checklist

- [ ] Confirm pinned SUSFS header/source/config dependencies and required feature guards
- [ ] Compare full upstream hunk with Rothko function control flow and VMA lifetime
- [ ] Verify unchanged behavior when SUSFS feature is disabled
- [ ] Verify enabled behavior does not bypass access authorization or page cleanup
- [ ] Test a minimal candidate patch on a disposable BSP checkout; keep upstream patch unchanged
- [ ] Review compilation and negative security contracts before any integration

**Status:** no source patch authored or applied. PR #9 Draft, release blocked. No merge, build, release, or flashing.
