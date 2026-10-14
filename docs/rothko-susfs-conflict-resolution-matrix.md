# Rothko SUSFS conflict resolution — measured baseline

Evidence: [read-only BSP anchor run 38326656541](https://github.com/cogan17/Xiomi-14t-pro/actions/runs/38326656541).

Exact checked-out `dev/rothko` baseline commit: `b2d8b54a0d8bb002d32dda24e58d2b5d0423546b`.

| Target | Baseline evidence | Decision | Next verification |
| --- | --- | --- | --- |
| `mm/memory.c` | SHA256 `55df841f1a648c433cd277c630b2aaadbb6d8633344ea7630678d177684ae191`; `linux/vmalloc.h` L78, `linux/sched/sysctl.h` L79, `linux/set_memory.h` L80, `trace/events/kmem.h` L82; `trace/hooks/mm.h` absent | Isolate include-context drift first; do not assume the missing hook header can be inserted or omitted safely | Compare official pinned patch's full `mm/memory.c` diff and its surrounding semantic additions; enumerate SUSFS header/source prerequisites |
| `fs/proc/task_mmu.c` | SHA256 `7eee0e599a5e1d7c3bb11d5d4c10a7e8abb0e801922c842e117345c76dbd6a85`; `struct mem_size_stats` present; `smaps_pte_range` present; `vma_pages(vma)` call absent | Semantic VMA port required; no blind replacement of upstream expression | Compare VMA traversal/accounting/locking and locate exact equivalent, if any, in target |

The mapper passed syntax/execution checks and verified the BSP checkout remained clean. These checks **do not** prove SUSFS integration, kernel compilation, runtime behavior, or security. The existing `provenance` gate intentionally remains blocking. Preserve upstream pins and PR #9 Draft; no merge, release, or flash.

## Next narrow deliverable

Generate an **upstream-vs-BSP per-hunk comparison** for `mm/memory.c` and `fs/proc/task_mmu.c` at these exact commits, with expected symbols and dependencies listed. Author a candidate patch only when the corresponding semantics are understood and the patch can be checked in an isolated checkout. No source deletion or overwrite of existing successful KSUN work.

## Existing integration candidates — scope correction (2026-10-14)

The original per-hunk comparison remains a provenance gate, **not** a request to recreate patches: existing candidates are `patches/rothko-susfs-memory-integrated-candidate.patch` and `patches/rothko-susfs-task-mmu-integrated-candidate.patch`. Neither is approved for build or runtime. Reuse these exact artifacts and do not duplicate their implementation.

- `mm/memory.c`: candidate checks `vma_lookup(mm, addr)` before `get_user_pages_remote()`. Verify mmap-lock lifetime, address progression and whether a missing/changed VMA can bypass the intended guard; confirm `susfs_def.h` and Kconfig dependencies.
- `fs/proc/task_mmu.c`: candidate covers `show_map_vma`, smaps, rollup and pagemap. The pagemap masking block derives `covered_end = start_vaddr + ((unsigned long)pm.pos << PAGE_SHIFT)` and indexes `pm.buffer` by `(mask_start - start_vaddr) >> PAGE_SHIFT`. **Open gate:** prove the unit and maximum of `pm.pos`, checked addition/shift bounds, alignment, buffer capacity, gaps between VMAs, and preservation of output entry count on the pinned BSP. The current source inspection alone does not establish these invariants.
- For both files, run the existing `scripts/rothko_susfs_hunk_compare.py` against the exact pinned official patch and pristine BSP first; treat nonunique/absent matches as semantic-port blockers, not permission to force a patch.
- Acceptance requires targeted isolated source-level evidence and negative boundary cases. No duplicate G2/G5 audit, no CI rerun without a specific unanswered gate, and no promotion of these candidates until dependencies and ownership are proven.

**Disposition:** candidate discovery complete; SUSFS memory/pagemap semantic verification remains OPEN. PR #9 Draft / BUILD HOLD unchanged.
