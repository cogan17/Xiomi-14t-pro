#!/usr/bin/env python3
"""Focused KSUN/SUSFS prerequisite patch composition; never builds a kernel."""
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from test_rothko_ksun_boot_status import NAMES as VERIFIED_STAGES
from test_rothko_ksun_g5_composition import PIN, git, require

EXTRA = (
    "susfs-builtin-only-mode-guard",
    "susfs-core-dependency",
    "susfs-lsm-kbuild-exclusion",
)
STAGES = VERIFIED_STAGES + EXTRA
CORE = "kernel/core/init.c"
CONFIG = "kernel/Kconfig"
KBUILD = "kernel/Kbuild"
NEW_TARGETS = {CORE, CONFIG, KBUILD}
EXPECTED_SCOPE = ({CORE, CONFIG}, {CONFIG}, {KBUILD})
BUILTIN_GUARD = (
    '#if defined(CONFIG_KSU_SUSFS) && defined(MODULE)\n'
    '#error "KernelSU SUSFS requires built-in mode: pinned SUSFS has no module teardown"\n'
    '#endif'
)
LSM_GUARD = (
    'ifeq ($(strip $(CONFIG_KPROBES)),y)\n'
    'ifneq ($(strip $(CONFIG_KSU_SUSFS)),y)\n'
    'kernelsu-objs += hook/lsm_hook.o\n'
    'endif\n'
    'ifdef KSU_ARCH\n'
)


def touched(patch):
    return set(re.findall(r"^--- a/(.+)$", patch.decode(), flags=re.M))


def rejected_apply(root, file):
    result = subprocess.run(
        ["git", "apply", "--check", "--whitespace=error", str(file)],
        cwd=root, capture_output=True, timeout=30,
    )
    require(result.returncode != 0, "missing prerequisite or duplicate was accepted")


def assert_contract(sources):
    core = sources[CORE]
    conf = sources[CONFIG]
    make = sources[KBUILD]
    require(core.count(BUILTIN_GUARD) == 1, "missing/duplicated built-in compilation guard")
    require("config KSU_SUSFS\n" in conf, "pinned KSU_SUSFS entry missing")
    stanza = conf.split("config KSU_SUSFS\n", 1)[1].split("\nconfig ", 1)[0]
    expected = (
        "\tdepends on KSU\n",
        "\tdepends on KSU=y\n",
        "\tdepends on THREAD_INFO_IN_TASK\n",
        "\tdepends on SUSFS\n",
    )
    positions = [stanza.find(item) for item in expected]
    require(all(stanza.count(item) == 1 for item in expected)
            and positions == sorted(positions), "Kconfig dependency/order changed")
    require(make.count("kernelsu-objs += hook/lsm_hook.o") == 1,
            "duplicate or missing LSM object")
    require(make.count(LSM_GUARD) == 1, "KPROBES/SUSFS nesting lost")
    require(make.count("kernelsu-objs += hook/$(KSU_ARCH)/patch_memory.o") == 1,
            "non-LSM KPROBES support unexpectedly removed")


def mutations(base):
    scenarios = (
        (CONFIG, "\tdepends on KSU=y\n", ""),
        (CONFIG, "\tdepends on SUSFS\n", ""),
        (CORE, BUILTIN_GUARD, ""),
        (KBUILD, "ifneq ($(strip $(CONFIG_KSU_SUSFS)),y)\n", ""),
        (KBUILD, "kernelsu-objs += hook/lsm_hook.o\n", ""),
        (KBUILD, "kernelsu-objs += hook/$(KSU_ARCH)/patch_memory.o\n", ""),
    )
    for path, old, replacement in scenarios:
        require(old in base[path], "negative target missing: " + path)
        broken = dict(base)
        broken[path] = broken[path].replace(old, replacement, 1)
        try:
            assert_contract(broken)
        except RuntimeError:
            continue
        raise RuntimeError("unsafe prerequisite mutation accepted: " + path)
    return len(scenarios)


def main():
    require(len(sys.argv) == 2,
            "usage: test_rothko_ksun_susfs_prerequisites.py PINNED_KSUN")
    upstream = Path(sys.argv[1]).resolve()
    require(git(upstream, "rev-parse", "HEAD").decode().strip() == PIN,
            "immutable KSUN pin mismatch")
    repo = Path(__file__).resolve().parents[1]
    patches = []
    all_paths = set()
    for name in STAGES:
        path = repo / "patches" / ("rothko-ksun-" + name + "-candidate.patch")
        patch = path.read_bytes().replace(b"\r\n", b"\n")
        paths = touched(patch)
        require(paths, "empty patch: " + name)
        if name in EXTRA:
            require(paths == EXPECTED_SCOPE[EXTRA.index(name)], "unexpected patch scope: " + name)
        patches.append((name, patch))
        all_paths.update(paths)
    originals = {p: git(upstream, "show", PIN + ":" + p) for p in all_paths}
    with tempfile.TemporaryDirectory(prefix="rothko-susfs-prereq-") as tmp:
        root = Path(tmp)
        git(root, "init", "-q")
        git(root, "config", "core.autocrlf", "false")
        for path, data in originals.items():
            output = root / path
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(data)
        applied = []
        baseline = None
        for index, (name, data) in enumerate(patches):
            candidate = root / (name + ".patch")
            candidate.write_bytes(data)
            if index == len(VERIFIED_STAGES):
                baseline = {p: (root / p).read_bytes() for p in all_paths}
                prerequisite = root / (EXTRA[1] + ".patch")
                prerequisite.write_bytes(patches[index + 1][1])
                rejected_apply(root, prerequisite)  # dependency needs KSU=y first
            flags = ["--unidiff-zero"] if index == 0 else []
            git(root, "apply", "--check", "--whitespace=error", *flags, str(candidate))
            git(root, "apply", "--whitespace=error", *flags, str(candidate))
            applied.append((candidate, flags))
        require(baseline is not None, "base chain incomplete")
        require(all((root / p).read_bytes() == data
                    for p, data in baseline.items() if p not in NEW_TARGETS),
                "previously validated non-target changed")
        sources = {p: (root / p).read_text(encoding="utf-8") for p in NEW_TARGETS}
        assert_contract(sources)
        count = mutations(sources)
        for name in EXTRA:
            rejected_apply(root, root / (name + ".patch"))
        for file, flags in reversed(applied):
            git(root, "apply", "--reverse", "--check", "--whitespace=error", *flags, str(file))
            git(root, "apply", "--reverse", "--whitespace=error", *flags, str(file))
        require(all((root / p).read_bytes() == data for p, data in originals.items()),
                "pin restoration did not exactly match")
        print("PASS: strict", len(STAGES), "stage apply/reverse; three existing SUSFS prerequisites")
        print("PASS:", count, "negative mutations; duplicate/dependency rejection")
        print("PASS:", len(all_paths), "pinned source files restored byte-for-byte")
        print("SOURCE ONLY: not a kernel compile, runtime, ABI/KMI or integration proof")


if __name__ == "__main__":
    main()
