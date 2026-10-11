#!/usr/bin/env python3
"""Source-lineage guard for development only. Read files, do not compile/flash."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs" / "ROTHKO_LINEAGE.json"


def fail(message):
    print("::error::" + message.replace("\n", " "))
    raise SystemExit(1)


def assignment(text, key):
    result = re.search(r"(?m)^" + re.escape(key) + r"[ \t]*=[ \t]*([0-9]+)\s*$", text)
    if not result:
        fail("Source assignment unavailable: " + key)
    return int(result.group(1))


def main():
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    source = evidence["xiaomi_source"]
    gki = evidence["gki_reference"]
    device = evidence["device_observation"]
    safety = evidence["prohibitions"]

    version_source = (ROOT / "Makefile").read_text(encoding="utf-8")
    actual_version = ".".join(str(assignment(version_source, key)) for key in (
        "VERSION", "PATCHLEVEL", "SUBLEVEL"
    ))
    if actual_version != source["makefile_kernel_version"]:
        fail("Rothko Makefile version changed: " + actual_version + "; re-audit source before proceeding.")

    kmi_file = (ROOT / "build.config.common").read_text(encoding="utf-8")
    kmi = assignment(kmi_file, "KMI_GENERATION")
    if kmi != source["build_config_kmi_generation"]:
        fail("Source KMI_GENERATION changed. Stop and re-audit.")

    if source["baseline_commit"] != "924d8eb314b764a92dc7d8610def9239f0db566c":
        fail("Source baseline changed; separately review provenance.")

    result = subprocess.run(["git", "hash-object", "Makefile"], cwd=ROOT,
                            capture_output=True, text=True, check=True)
    if result.stdout.strip() != source["makefile_blob_sha"]:
        fail("Makefile blob no longer matches audited Xiaomi baseline. Stop.")

    if gki["repository"] != "cogan17/GKI_BakaSU_SUSFS":
        fail("Unexpected reference repository.")
    if gki["requested_manifest_branch"] != "common-android14-6.1-lts":
        fail("Reference GKI source manifest branch changed.")
    if gki["requested_kernel_version"] != "6.1.177":
        fail("Reference GKI requested sublevel changed; re-audit.")
    if gki["compiled_kernel_commit_confirmed"] is not False:
        fail("An asserted binary build provenance requires independent verification.")

    if actual_version == gki["requested_kernel_version"]:
        fail("Rothko baseline became indistinguishable from GKI request; verify lineage.")
    if device["codename"] != "rothko" or device["uname_is_susfs_spoofed"] is not True:
        fail("Device observation/spoofing constraints unexpectedly changed.")
    for field in ("true_running_kernel_version_verified",
                  "vendor_module_abi_verified",
                  "partition_layout_verified",
                  "flashable_compatibility_verified"):
        if device[field] is not False:
            fail("Device compatibility must not be approved from a source-only audit: " + field)
    for field, value in safety.items():
        if value is not True:
            fail("Safety policy changed without review: " + field)

    message = [
        "# Cogan Rothko - source lineage (static check only)",
        "",
        "| Property | Audited information |",
        "|---|---|",
        "| Xiaomi source Makefile | " + actual_version + " |",
        "| Xiaomi source KMI_GENERATION | " + str(kmi) + " |",
        "| Xiaomi source commit | " + source["baseline_commit"] + " |",
        "| GKI project | " + gki["repository"] + " |",
        "| GKI AOSP manifest requested | " + gki["requested_manifest_branch"] + " |",
        "| GKI custom workflow requested version | " + gki["requested_kernel_version"] + " (request, not verified binary) |",
        "| Device uname | SUSFS-spoofed; actual version **unknown** |",
        "| Vendor module ABI | NOT VERIFIED |",
        "| Flashable device compatibility | **BLOCKED** |",
        "",
        "**Result: static provenance checks PASS, device compatibility NOT APPROVED.**",
        "",
        "No kernel compilation, root/patch installation, artifact or device modification.",
    ]
    rendered = "\n".join(message) + "\n"
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as out:
            out.write(rendered)
    print(rendered)


if __name__ == "__main__":
    main()
