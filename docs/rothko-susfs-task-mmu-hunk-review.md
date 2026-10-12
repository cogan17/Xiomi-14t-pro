# SUSFS Rothko: fs/proc/task_mmu.c rejected hunk

Evidence: official Simonpunk SUSFS gki-android14-6.1 patch dry-run, Actions run 38236950368, job 114769847590, failed at `fs/proc/task_mmu.c:883`. Three earlier hunks in this file passed with offset -1.

Patch's expected context: `struct vm_area_struct *vma = v; struct mem_size_stats mss; memset(&mss, 0, sizeof(mss)); if (!vma_pages(vma)) ...`.

Actual pristine Xiaomi `dev/rothko:fs/proc/task_mmu.c`: `show_smap()` at line 867; `vma` and `mss` declarations at 869-870; `memset` at 872; then **`smap_gather_stats(vma, &mss, 0);` at 874**, followed by `show_map_vma()` and output fields. The expected `if (!vma_pages(vma))` branch is absent at this location. The same file also has a distinct `show_smaps_rollup()` at 895 and `memset` at 914, with `mmap_read_lock_killable()` at 916.

Classification: **control-flow divergence in smaps**, not a simple include or line-offset mismatch. The upstream patch assumes an early VMA page-count guard that this BSP does not have. Do not insert it or skip `smap_gather_stats` without checking semantics; preserve existing Android vendor `trace_android_vh_show_smap()` (around 864), accounting and mmap locking.

Gate: retrieve exact upstream patch additions/removals for this hunk and identify what SUSFS intends to filter before deciding whether `show_smap`, `show_smaps_rollup`, or an earlier maps iterator is the correct integration point. No source modifications, builds, or flash. PR remains Draft.
