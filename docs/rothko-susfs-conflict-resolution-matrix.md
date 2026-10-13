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
