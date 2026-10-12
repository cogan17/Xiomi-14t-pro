# SUSFS Rothko: fs/proc/base.c rejected include hunk

Evidence: official Simonpunk SUSFS 6.1 patch dry-run in Actions run 38236950368, job 114769847590. Failed at `fs/proc/base.c:100`.

The upstream patch expected `linux/cn_proc.h`, `linux/cpufreq_times.h`, **`linux/dma-buf.h`**, `trace/events/oom.h`, `trace/hooks/sched.h`, and `internal.h` in sequence. The pristine Xiaomi Rothko BSP `dev/rothko:fs/proc/base.c` at lines 98–103 instead has `linux/cn_proc.h`, `linux/cpufreq_times.h`, `trace/events/oom.h`, `trace/hooks/sched.h`, `internal.h`, and `fd.h`.

**Classification:** include-context mismatch. The missing `linux/dma-buf.h` line prevents this patch hunk matching; the additional `fd.h` follows after the expected sequence. This is not evidence that the actual SUSFS proc visibility hooks are safe or unsafe.

**Gate:** inspect the precise added/deleted lines of this upstream hunk, then check whether SUSFS needs new includes and whether its `/proc` behavior overlaps existing vendor hooks. Do not add a dummy `dma-buf.h` line solely to make `git apply --check` pass. No source edits, build or flashing. PR remains Draft.
