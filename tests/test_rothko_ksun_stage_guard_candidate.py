#!/usr/bin/env python3
"""Negative mutations for isolated KSUN G3 source candidate.

All changes stay in a temporary copy of runtime/ksud_integration.c.
The guards being detected are NOT a proven safe retry implementation.
"""
from pathlib import Path
import subprocess
import sys
import tempfile

# label, segment, old, new. All replacements are within a scoped CONFIG/marker.
MUTATIONS = (
    ("SUSFS second-stage ignores status", "susfs_init",
     "if (setup_ksu_cred()) {", "if (false) {"),
    ("SUSFS second-stage error continues", "susfs_init",
     "return 0;", "/* continue despite error */"),
    ("SUSFS zygote ignores status", "susfs_zygote",
     "if (setup_ksu_cred()) {", "if (false) {"),
    ("SUSFS zygote error continues", "susfs_zygote",
     "return 0;", "/* continue despite error */"),
    ("non-SUSFS second-stage ignores status", "nonsusfs_init",
     "if (setup_ksu_cred()) {", "if (false) {"),
    ("non-SUSFS second-stage error continues", "nonsusfs_init",
     "return;", "/* continue despite error */"),
    ("SUSFS second-stage stage key removed", "susfs_init",
     "static_branch_disable(&is_init_second_stage_not_executed);", "/* key disabled too late */"),
    ("SUSFS zygote stage key removed", "susfs_zygote",
     "static_branch_disable(&is_first_zygote);", "/* key never disabled */"),
)


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: test_rothko_ksun_stage_guard_candidate.py KERNEL_ROOT VALIDATOR", file=sys.stderr)
        return 2
    source = Path(sys.argv[1]) / "runtime/ksud_integration.c"
    validator = Path(sys.argv[2])
    original = source.read_text(encoding="utf-8")
    start = original.index("#ifdef CONFIG_KSU_SUSFS\nextern int ksu_handle_execveat_init")
    middle = original.index("#else\nvoid ksu_handle_execveat_ksud", start)
    end = original.index("#endif\n\nstatic ssize_t", middle)
    zygote = original.index("if (static_branch_unlikely(&is_first_zygote))", start)
    ranges = {
        "susfs_init": (start, zygote),
        "susfs_zygote": (zygote, middle),
        "nonsusfs_init": (middle, end),
    }

    with tempfile.TemporaryDirectory(prefix="rothko-g3-") as td:
        root = Path(td)
        dst = root / "runtime/ksud_integration.c"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(original, encoding="utf-8")

        def audit(*flags):
            return subprocess.run(
                [sys.executable, str(validator), str(root), *flags],
                capture_output=True, text=True, timeout=20, check=False)

        baseline = audit()
        if baseline.returncode != 0 or "RELEASE GATE: BLOCKED" not in baseline.stdout:
            raise RuntimeError("G3 baseline source audit must pass while release remains blocked:\n"
                               + baseline.stdout + baseline.stderr)
        gate = audit("--require-safe-retry")
        if gate.returncode != 3 or "RETRY GATE: DENIED" not in gate.stderr:
            raise RuntimeError("G3 retry gate failed to deny unreviewed reentrancy")
        print("PASS: G3 retry gate remains denied (idempotence unproven)", flush=True)

        for label, scope, old, new in MUTATIONS:
            lo, hi = ranges[scope]
            pos = original.find(old, lo, hi)
            if pos < 0:
                raise RuntimeError(f"{label}: target not in intended source segment")
            edited = original[:pos] + new + original[pos+len(old):]
            dst.write_text(edited, encoding="utf-8")
            result = audit()
            dst.write_text(original, encoding="utf-8")
            if result.returncode != 1 or "REVIEW REQUIRED" not in result.stdout:
                raise RuntimeError(f"{label}: regression not detected:\n"+result.stdout+result.stderr)
            print("PASS: rejected G3 source mutation — " + label, flush=True)
    print("PASS: eight G3 mutations detected; integration/release STILL BLOCKED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeError, RuntimeError, subprocess.TimeoutExpired, ValueError) as exc:
        print("FAIL: " + str(exc), file=sys.stderr)
        raise SystemExit(1)
