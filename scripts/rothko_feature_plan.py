#!/usr/bin/env python3
"""Rothko Stage 1: validate UI choices without modifying kernel source."""
import json
import os
from pathlib import Path

ROOTS = {
    "KernelSU": ["KernelSU"],
    "KernelSU-Next": ["KernelSU-Next"],
    "BakaSU": ["BakaSU"],
    "All (KSU + KSUN + BakaSU)": ["KernelSU", "KernelSU-Next", "BakaSU"],
}
FEATURES = (
    ("susfs", "SUSFS"),
    ("nomount", "NoMount"),
    ("baseband_guard", "Baseband Guard"),
    ("networking", "Networking"),
    ("ptrace_patch", "Ptrace Patch"),
    ("unicode_fix", "Unicode Fix"),
    ("bpf_stack", "BPF Stack (BTF + eBPF + FUSE-BPF)"),
    ("performance", "Performance"),
    ("release_notes_preview", "Render release notes preview only"),
)

def select(root, inputs, ref):
    if ref != "refs/heads/dev/rothko":
        raise ValueError("This no-build workflow is restricted to dev/rothko")
    if root not in ROOTS:
        raise ValueError("Unsupported root selection: " + repr(root))
    if set(inputs) != {name for name, _ in FEATURES}:
        raise ValueError("Expected exactly the nine supported feature flags")
    for name, raw in inputs.items():
        if raw not in ("true", "false"):
            raise ValueError(f"{name}: expected true/false, got {raw!r}")
    return ROOTS[root], {name: inputs[name] == "true" for name, _ in FEATURES}

def summary(root, variants, flags):
    lines = [
        "# Cogan Rothko — Root and Feature Plan", "",
        f"Root flavor: **{root}**", "",
        "Planned independent root variants:",
        *[f"- {variant}" for variant in variants],
        "", "| Feature (request only) | Selected |", "|---|---|",
        *[f"| {label} | {str(flags[name]).lower()} |" for name, label in FEATURES],
    ]
    if flags["release_notes_preview"]:
        lines.extend(["", "Release notes preview only: root-variant jobs are skipped."])
    lines.extend([
        "", "**PLAN ONLY: no root installation, patching, compilation, release or flashable ZIP.**",
        "DroidSpaces, NTSync, and GKI BakaSU-specific ZRAM/Re-Kernel/CVE toggles are absent.",
        "Selected features have NOT been proven compatible with Rothko BSP or vendor ABI/KMI.",
        "",
    ])
    return "\n".join(lines)

def main():
    root = os.environ.get("ROOT_FLAVOR", "")
    raw = {name: os.environ.get(name.upper(), "") for name, _ in FEATURES}
    variants, flags = select(root, raw, os.environ.get("GITHUB_REF", ""))
    with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as handle:
        handle.write("root_matrix=" + json.dumps(variants, separators=(",", ":")) + "\n")
        handle.write("features_json=" + json.dumps(flags, separators=(",", ":")) + "\n")
    with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as handle:
        handle.write(summary(root, variants, flags))
    print(f"Validated {len(variants)} independent root plan(s); no build.")

if __name__ == "__main__":
    try:
        main()
    except (KeyError, ValueError) as exc:
        raise SystemExit(f"::error::{exc}") from exc
