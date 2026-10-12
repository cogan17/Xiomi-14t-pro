# SUSFS Rothko: mm/memory.c rejected hunk

Evidence: read-only `git apply --check --verbose` on official Simonpunk `gki-android14-6.1` patch, Actions run 38236950368, job 114769847590, rejected at `mm/memory.c:79`.

Expected patch context: `#include <linux/vmalloc.h>`, `#include <linux/sched/sysctl.h>`, `#include <linux/set_memory.h>`, blank line, `#include <trace/events/kmem.h>`, **`#include <trace/hooks/mm.h>`**.

Pristine Xiaomi `dev/rothko:mm/memory.c` lines 78–84: same three linux includes and `trace/events/kmem.h`, but **no `trace/hooks/mm.h`**; line 84 is blank, followed by architecture includes. No occurrence of `trace/hooks/mm.h` or `susfs` in this file. `__handle_mm_fault` occurs around line 5145 and `handle_mm_fault` around 5335, but the failed hunk is in the include section; no behavioral fault-path conflict has been established.

Classification: include-context mismatch. Do not add the missing Android trace header merely to make upstream patch apply; inspect upstream added lines and whether this BSP provides the header and matching hooks first. Preserve Xiaomi page-fault behavior.

Five rejected files are now **mapped**, not fixed: `fs/exec.c`, `fs/namei.c`, `fs/proc/base.c`, `fs/proc/task_mmu.c`, `mm/memory.c`. Next gate: retrieve exact upstream patch diff hunks, compare semantic dependencies and KSUN/SELinux hook ownership, and only then propose a Rothko-specific adaptation. No kernel source edits, compilation or flashing; PR Draft.
